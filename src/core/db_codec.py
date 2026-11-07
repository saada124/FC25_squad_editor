import struct
from typing import Dict, List, Tuple, Any, Optional

def get_bits(data: bytes, bit_offset: int, bit_size: int) -> int:
    """Extracts an integer value from a bit-packed binary record."""
    if bit_size <= 0:
        return 0
    byte_start = bit_offset // 8
    byte_end = (bit_offset + bit_size + 7) // 8
    chunk = data[byte_start:byte_end]
    val = int.from_bytes(chunk, "little")
    shift = bit_offset % 8
    mask = (1 << bit_size) - 1
    return (val >> shift) & mask

def set_bits(data: bytearray, bit_offset: int, bit_size: int, new_val: int) -> None:
    """Writes an integer value into a bit-packed binary record without disturbing adjacent bits."""
    if bit_size <= 0:
        return
    byte_start = bit_offset // 8
    byte_end = (bit_offset + bit_size + 7) // 8
    chunk_len = byte_end - byte_start
    val = int.from_bytes(data[byte_start:byte_end], "little")
    shift = bit_offset % 8
    mask = (1 << bit_size) - 1
    val &= ~(mask << shift)
    val |= (new_val & mask) << shift
    data[byte_start:byte_end] = val.to_bytes(chunk_len, "little")

class DBColumn:
    def __init__(self, sname: str, bit_size: int, col_type: int, bit_offset: int, display_name: str = ""):
        self.sname = sname
        self.bit_size = bit_size
        self.col_type = col_type # 3 = int/bitfield, 0 = string, 4 = float
        self.bit_offset = bit_offset
        self.display_name = display_name or sname
        self.is_trailer = False

    def decode_value(self, record_bytes: bytes) -> Any:
        if self.col_type == 0: # String
            byte_start = self.bit_offset // 8
            null_idx = record_bytes.find(b"\x00", byte_start)
            if null_idx != -1:
                raw = record_bytes[byte_start:null_idx]
            else:
                raw = record_bytes[byte_start:]
            try:
                return raw.decode("utf-8").strip()
            except Exception:
                return raw.decode("latin-1", errors="replace").strip()
        elif self.col_type == 4: # Float
            if self.bit_size == 32:
                raw_int = get_bits(record_bytes, self.bit_offset, 32)
                return round(struct.unpack("<f", struct.pack("<I", raw_int))[0], 3)
            elif self.bit_size == 16:
                raw_int = get_bits(record_bytes, self.bit_offset, 16)
                return round(struct.unpack("<e", struct.pack("<H", raw_int))[0], 3)
            else:
                return get_bits(record_bytes, self.bit_offset, self.bit_size)
        else: # 3 = Integer / Bitfield
            return get_bits(record_bytes, self.bit_offset, self.bit_size)

    def encode_value(self, record_bytes: bytearray, val: Any) -> None:
        if self.col_type == 0: # String
            byte_start = self.bit_offset // 8
            text_bytes = str(val if val is not None else "").encode("latin-1", errors="replace") + b"\x00"
            max_avail = len(record_bytes) - byte_start
            to_write = text_bytes[:max_avail]
            record_bytes[byte_start:byte_start + len(to_write)] = to_write
        elif self.col_type == 4: # Float
            try:
                flt_val = float(val)
                if self.bit_size == 32:
                    raw_int = struct.unpack("<I", struct.pack("<f", flt_val))[0]
                    set_bits(record_bytes, self.bit_offset, 32, raw_int)
                elif self.bit_size == 16:
                    raw_int = struct.unpack("<H", struct.pack("<e", flt_val))[0]
                    set_bits(record_bytes, self.bit_offset, 16, raw_int)
                else:
                    int_val = int(flt_val)
                    mask = (1 << self.bit_size) - 1
                    clamped = max(0, min(int_val, mask))
                    set_bits(record_bytes, self.bit_offset, self.bit_size, clamped)
            except Exception:
                pass
        else: # 3 = Integer / Bitfield
            try:
                int_val = int(val)
                mask = (1 << self.bit_size) - 1
                clamped = max(0, min(int_val, mask))
                set_bits(record_bytes, self.bit_offset, self.bit_size, clamped)
            except Exception:
                pass

class DBTable:
    def __init__(self, sname: str, offset: int, display_name: str = ""):
        self.sname = sname
        self.offset = offset
        self.display_name = display_name or sname
        self.header_raw = bytearray()
        self.rec_size = 0
        self.max_records = 0
        self.num_cols = 0
        self.written_records = 0
        self.columns: List[DBColumn] = []
        self.columns_map: Dict[str, DBColumn] = {}
        self.records: List[bytearray] = []
        self.header_size = 0
        self.is_alt_header = False
        self.trailing_bytes = bytearray()

    def parse(self, db_payload: bytes, table_data_base: int, next_offset: int):
        abs_table_start = table_data_base + self.offset
        tbl_slice = db_payload[abs_table_start:table_data_base + next_offset]
        
        self.header_raw = bytearray(tbl_slice[:48])
        ints = struct.unpack("<12I", self.header_raw)
        
        self.rec_size = ints[2]
        self.max_records = ints[3]
        self.written_records = struct.unpack("<H", self.header_raw[20:22])[0]
        self.num_cols = self.header_raw[28]
        
        # Universal FIFA DB v8 column layout:
        # First (num_cols - 1) columns are 16 bytes: sname(4), bit_size(4), col_type(4), bit_offset(4)
        # Last column is 8 bytes: sname(4), bit_size(4)
        self.header_size = 48 + (self.num_cols - 1) * 16 + 8 if self.num_cols > 0 else 48
            
        desc_bytes = tbl_slice[48:self.header_size]
        self.columns.clear()
        self.columns_map.clear()
        
        for ci in range(self.num_cols - 1):
            chunk = desc_bytes[ci*16 : (ci+1)*16]
            if len(chunk) < 16: break
            c_sname = chunk[:4].decode("latin-1")
            bit_size, col_type, bit_offset = struct.unpack("<III", chunk[4:16])
            # Guard against packed string buffer length or anomalies leaking into integer bit_size
            if col_type == 3 and (bit_size + bit_offset > self.rec_size * 8):
                bit_size = min(32, max(1, self.rec_size * 8 - bit_offset))
            col = DBColumn(c_sname, bit_size, col_type, bit_offset)
            col.is_trailer = False
            self.columns.append(col)
            self.columns_map[c_sname] = col
            
        if self.num_cols > 0:
            last_chunk = desc_bytes[(self.num_cols - 1)*16 : (self.num_cols - 1)*16 + 8]
            if len(last_chunk) >= 8:
                c_sname = last_chunk[:4].decode("latin-1")
                bit_size = struct.unpack("<I", last_chunk[4:8])[0]
                trailer_offset = max(0, self.rec_size * 8 - bit_size)
                col = DBColumn(c_sname, bit_size, 3, trailer_offset)
                col.is_trailer = True
                self.columns.append(col)
                self.columns_map[c_sname] = col
                    
        records_start = self.header_size
        self.records.clear()
        if self.rec_size > 0:
            count = self.written_records
            if count == 0 and len(tbl_slice) > records_start:
                count = (len(tbl_slice) - records_start) // self.rec_size
            self.written_records = count
            rec_bytes_len = count * self.rec_size
            for r in range(count):
                r_start = records_start + (r * self.rec_size)
                self.records.append(bytearray(tbl_slice[r_start:r_start + self.rec_size]))
            self.trailing_bytes = bytearray(tbl_slice[records_start + rec_bytes_len:])
        else:
            self.written_records = 0
            self.trailing_bytes = bytearray(tbl_slice[records_start:])

    def serialize(self) -> bytes:
        if len(self.header_raw) >= 22:
            struct.pack_into("<H", self.header_raw, 20, len(self.records))
            
        out = bytearray()
        out.extend(self.header_raw)
        for col in self.columns:
            out.extend(col.sname.encode("latin-1")[:4].ljust(4, b"\x00"))
            if getattr(col, "is_trailer", False):
                out.extend(struct.pack("<I", col.bit_size))
            else:
                out.extend(struct.pack("<III", col.bit_size, col.col_type, col.bit_offset))
        for rec in self.records:
            out.extend(rec)
        out.extend(self.trailing_bytes)
        return bytes(out)

    def export_to_csv(self, filepath: str, include_labels: bool = True) -> Tuple[bool, str, int]:
        """
        Exports all records in this table to a CSV file.
        Uses UTF-8-sig encoding for perfect compatibility with Microsoft Excel, LibreOffice, and Calc.
        """
        import csv
        try:
            try:
                from src.core.schema import get_column_display_name
            except ImportError:
                try:
                    from core.schema import get_column_display_name
                except ImportError:
                    get_column_display_name = lambda c, t="": c

            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                headers = []
                for col in self.columns:
                    disp = get_column_display_name(col.sname, self.sname) if include_labels else ""
                    if disp and disp != col.sname:
                        headers.append(f"{col.sname} [{disp}]")
                    else:
                        headers.append(col.sname)
                writer.writerow(headers)

                row_count = 0
                for rec in self.records:
                    row_vals = [col.decode_value(rec) for col in self.columns]
                    writer.writerow(row_vals)
                    row_count += 1
            return True, f"Successfully exported {row_count:,} records to {filepath}", row_count
        except Exception as e:
            return False, f"Failed to export CSV: {str(e)}", 0

    def import_from_csv(self, filepath: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Imports records from a CSV file into this table.
        Matches columns by 4-character shortname (supports 'wDHM' or 'wDHM [Overall]').
        Validates bit-ranges and updates in-place or appends new rows.
        """
        import csv
        stats = {"rows_read": 0, "rows_updated": 0, "rows_appended": 0, "columns_matched": 0}
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                try:
                    raw_headers = next(reader)
                except StopIteration:
                    return False, "CSV file is empty", stats

                col_index_map: Dict[int, DBColumn] = {}
                for idx, h in enumerate(raw_headers):
                    h_clean = h.strip()
                    sname = h_clean.split()[0].replace("[", "").replace("]", "")[:4]
                    if sname in self.columns_map:
                        col_index_map[idx] = self.columns_map[sname]

                stats["columns_matched"] = len(col_index_map)
                if not col_index_map:
                    return False, "No matching table columns found in CSV header", stats

                row_idx = 0
                for row in reader:
                    stats["rows_read"] += 1
                    if row_idx < len(self.records):
                        rec = self.records[row_idx]
                        stats["rows_updated"] += 1
                    else:
                        rec = bytearray(self.rec_size)
                        self.records.append(rec)
                        stats["rows_appended"] += 1

                    for c_idx, val_str in enumerate(row):
                        if c_idx in col_index_map:
                            col = col_index_map[c_idx]
                            col.encode_value(rec, val_str.strip())
                    row_idx += 1

                self.written_records = len(self.records)
                msg = f"Imported {stats['rows_read']:,} rows ({stats['rows_updated']:,} updated, {stats['rows_appended']:,} appended) across {stats['columns_matched']} columns."
                return True, msg, stats
        except Exception as e:
            return False, f"Failed to import CSV: {str(e)}", stats

class FIFADatabase:
    """
    Parses and serializes the complete FIFA DB v8 relational database structure (all 76 tables).
    """
    def __init__(self):
        self.header_pre = bytearray()
        self.table_count = 0
        self.table_toc: List[Tuple[str, int]] = []
        self.tables: List[DBTable] = []
        self.tables_map: Dict[str, DBTable] = {}
        self.table_data_base = 0

    def parse(self, db_payload: bytes):
        if db_payload[:4] != b"DB\x00\x08":
            raise ValueError("Invalid DB payload magic")
            
        self.header_pre = bytearray(db_payload[:24])
        self.table_count = struct.unpack("<I", db_payload[16:20])[0]
        
        self.table_toc.clear()
        for i in range(self.table_count):
            entry = db_payload[24 + i*8 : 24 + (i+1)*8]
            sname = entry[:4].decode("latin-1")
            offset = struct.unpack("<I", entry[4:8])[0]
            self.table_toc.append((sname, offset))
            
        self.table_data_base = 24 + (self.table_count * 8)
        total_db_len = len(db_payload)
        
        self.tables.clear()
        self.tables_map.clear()
        
        for i, (sname, offset) in enumerate(self.table_toc):
            next_offset = self.table_toc[i+1][1] if i+1 < len(self.table_toc) else (total_db_len - self.table_data_base)
            tbl = DBTable(sname, offset)
            tbl.parse(db_payload, self.table_data_base, next_offset)
            self.tables.append(tbl)
            self.tables_map[sname] = tbl

    def serialize(self) -> bytes:
        serialized_tables = []
        for tbl in self.tables:
            serialized_tables.append(tbl.serialize())
            
        toc_entries = []
        current_offset = 0
        for i, tbl in enumerate(self.tables):
            toc_entries.append((tbl.sname, current_offset))
            current_offset += len(serialized_tables[i])
            
        out = bytearray()
        out.extend(self.header_pre)
        for sname, offset in toc_entries:
            out.extend(sname.encode("latin-1")[:4].ljust(4, b"\x00"))
            out.extend(struct.pack("<I", offset))
            
        for t_bytes in serialized_tables:
            out.extend(t_bytes)
            
        return bytes(out)
