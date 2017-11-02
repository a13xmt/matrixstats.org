MOST_INCOMERS_PER_PERIOD_QUERY = """
SELECT * from (
  SELECT
  td.room_id as room_id,
  COALESCE(fd.members_count, 0) as members_from,
  td.members_count as members_to,
  fd.date as date_from,
  td.date as date_to,
  td.members_count - COALESCE(fd.members_count, 0) as delta,
  (td.members_count::decimal / COALESCE(fd.members_count, 1) - 1) * 100 as percentage
  FROM
  (
    SELECT DISTINCT ON (room_id) dm.*
    FROM room_stats_dailymembers dm
    WHERE date <= '%(to_date)s'
    ORDER BY room_id, date DESC
  ) td
  LEFT JOIN
  (
    SELECT DISTINCT ON (room_id) dm.*
    FROM room_stats_dailymembers dm
    WHERE date <= '%(from_date)s'
    ORDER BY room_id, date DESC
  ) fd
  ON fd.room_id = td.room_id
  WHERE td.members_count > 15 or fd.members_count > 15
) as rs, room_stats_room r
WHERE rs.room_id = r.id
ORDER BY %(order_by)s DESC;
"""

NEW_ROOMS_FOR_LAST_N_DAYS_QUERY = """
  SELECT * FROM (
    SELECT room_id FROM (
        SELECT room_id, count(1)
        FROM room_stats_dailymembers
        GROUP BY room_id
    ) as rds
    WHERE count <= %s
  ) as rc
  LEFT JOIN room_stats_room as r
  ON r.id = rc.room_id
  WHERE r.id != ''
  ORDER BY members_count DESC;
"""
