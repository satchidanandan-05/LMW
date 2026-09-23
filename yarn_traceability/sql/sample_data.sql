-- Demo data. Users are inserted by init_database() before this file runs (created_by = 2 is operator1).

-- Machine masters
INSERT INTO autoconer (autoconer_id, machine_name) VALUES
    ('AC-01', 'Autoconer 1'), ('AC-02', 'Autoconer 2'), ('AC-03', 'Autoconer 3');

INSERT INTO drum (drum_id, autoconer_id) VALUES
    ('D011', 'AC-01'), ('D012', 'AC-01'),
    ('D025', 'AC-02'), ('D026', 'AC-02'),
    ('D031', 'AC-03'), ('D032', 'AC-03');

INSERT INTO speedframe (speedframe_id, machine_name) VALUES
    ('SF-01', 'Speedframe 1'), ('SF-02', 'Speedframe 2'), ('SF-03', 'Speedframe 3'),
    ('SF-04', 'Speedframe 4'), ('SF-05', 'Speedframe 5');

INSERT INTO spindle (spindle_id, speedframe_id) VALUES
    ('S101', 'SF-01'), ('S102', 'SF-01'), ('S103', 'SF-01'), ('S104', 'SF-01'),
    ('S128', 'SF-02'), ('S129', 'SF-02'), ('S130', 'SF-02'), ('S131', 'SF-02'),
    ('S150', 'SF-03'), ('S151', 'SF-03'), ('S152', 'SF-03'), ('S153', 'SF-03'),
    ('S170', 'SF-04'), ('S171', 'SF-04'), ('S172', 'SF-04'), ('S173', 'SF-04'),
    ('S210', 'SF-05'), ('S211', 'SF-05'), ('S212', 'SF-05'), ('S213', 'SF-05');

-- Yarn cones
INSERT INTO yarn_cone (cy_id, drum_id, cone_scan_datetime, receive_txn_id, created_by, created_at) VALUES
    ('YC001', 'D011', '2026-09-19 10:00:00', 'seed-yc001', 2, '2026-09-19 10:00:00'),
    ('YC002', 'D012', '2026-09-19 14:30:00', 'seed-yc002', 2, '2026-09-19 14:30:00'),
    ('YC006', 'D025', '2026-09-20 11:12:09', 'seed-yc006', 2, '2026-09-20 11:12:09'),  -- example image
    ('YC007', 'D026', '2026-09-21 09:00:00', 'seed-yc007', 2, '2026-09-21 09:00:00'),  -- PARTIAL: no COBs
    ('YC008', 'D031', '2026-09-21 10:00:00', 'seed-yc008', 2, '2026-09-21 10:00:00');  -- INCONSISTENT

-- COBs
INSERT INTO cob (cob_id, spindle_id, cob_scan_datetime, receive_txn_id, created_by, created_at) VALUES
    ('COB001', 'S101', '2026-09-19 07:10:00', 'seed-yc001', 2, '2026-09-19 10:00:00'),
    ('COB002', 'S102', '2026-09-19 07:12:30', 'seed-yc001', 2, '2026-09-19 10:00:00'),
    ('COB003', 'S150', '2026-09-19 12:00:00', 'seed-yc002', 2, '2026-09-19 14:30:00'),
    ('COB004', 'S128', '2026-09-20 08:05:12', 'seed-yc006', 2, '2026-09-20 11:12:09'),
    ('COB005', 'S129', '2026-09-20 08:06:18', 'seed-yc006', 2, '2026-09-20 11:12:09'),
    ('COB015', 'S210', '2026-09-20 09:14:33', 'seed-yc006', 2, '2026-09-20 11:12:09'),
    ('COB020', 'S170', '2026-09-21 09:30:00', 'seed-yc008', 2, '2026-09-21 10:00:00'),
    ('COB021', 'S171', '2026-09-21 10:45:00', 'seed-yc008', 2, '2026-09-21 10:00:00'),  -- after its cone
    ('COB099', 'S130', '2026-09-22 08:00:00', 'seed-orphan', 2, '2026-09-22 08:00:00'); -- orphan

-- COB -> Yarn Cone links
INSERT INTO cob_traceability (cy_id, cob_id, receive_txn_id, created_at) VALUES
    ('YC001', 'COB001', 'seed-yc001', '2026-09-19 10:00:00'),
    ('YC001', 'COB002', 'seed-yc001', '2026-09-19 10:00:00'),
    ('YC002', 'COB003', 'seed-yc002', '2026-09-19 14:30:00'),
    ('YC006', 'COB004', 'seed-yc006', '2026-09-20 11:12:09'),
    ('YC006', 'COB005', 'seed-yc006', '2026-09-20 11:12:09'),
    ('YC006', 'COB015', 'seed-yc006', '2026-09-20 11:12:09'),
    ('YC008', 'COB020', 'seed-yc008', '2026-09-21 10:00:00'),
    ('YC008', 'COB021', 'seed-yc008', '2026-09-21 10:00:00');
