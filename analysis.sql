-- Research questions answered with SQL (works in MySQL, and in SQLite for testing).
-- Ceiling prices exclude GST, Jan Aushadhi MRP includes it, so GST (from the settings table) is added to the ceiling price.
-- Savings % = (ceiling price incl. GST - Jan Aushadhi price) / ceiling price incl. GST x 100, per tablet/capsule.

-- Q1. How many Jan Aushadhi products could be compared?
SELECT COUNT(*) AS products_with_price,
       SUM(CASE WHEN price_per_unit IS NOT NULL AND strength_key <> '' THEN 1 ELSE 0 END) AS tablets_capsules_comparable,
       (SELECT COUNT(*) FROM medicine_matches) AS matched_to_ceiling_price
FROM ja_medicines;

-- Q2. Overall: how much cheaper is Jan Aushadhi than the maximum allowed (ceiling) price?
SELECT COUNT(*) AS medicines,
       ROUND(AVG(100.0 * (c.ceiling_price * (1 + s.value / 100.0) - j.price_per_unit) / (c.ceiling_price * (1 + s.value / 100.0))), 1) AS avg_saving_pct,
       ROUND(MIN(100.0 * (c.ceiling_price * (1 + s.value / 100.0) - j.price_per_unit) / (c.ceiling_price * (1 + s.value / 100.0))), 1) AS min_saving_pct,
       ROUND(MAX(100.0 * (c.ceiling_price * (1 + s.value / 100.0) - j.price_per_unit) / (c.ceiling_price * (1 + s.value / 100.0))), 1) AS max_saving_pct,
       SUM(CASE WHEN j.price_per_unit <= 0.5 * c.ceiling_price * (1 + s.value / 100.0) THEN 1 ELSE 0 END) AS at_least_half_price
FROM medicine_matches m
JOIN ja_medicines j ON j.drug_code = m.drug_code
JOIN ceiling_prices c ON c.ceiling_id = m.ceiling_id
JOIN settings s ON s.name = 'gst_percent';

-- Q3. Savings by therapeutic group (groups with at least 5 matched medicines, so averages are meaningful)
SELECT j.group_name, COUNT(*) AS medicines,
       ROUND(AVG(100.0 * (c.ceiling_price * (1 + s.value / 100.0) - j.price_per_unit) / (c.ceiling_price * (1 + s.value / 100.0))), 1) AS avg_saving_pct
FROM medicine_matches m
JOIN ja_medicines j ON j.drug_code = m.drug_code
JOIN ceiling_prices c ON c.ceiling_id = m.ceiling_id
JOIN settings s ON s.name = 'gst_percent'
GROUP BY j.group_name
HAVING COUNT(*) >= 5
ORDER BY avg_saving_pct DESC;

-- Q4. Every matched medicine, with both prices per tablet/capsule
SELECT j.drug_code, j.generic_name, j.group_name,
       ROUND(j.price_per_unit, 2) AS jan_aushadhi_per_unit,
       ROUND(c.ceiling_price * (1 + s.value / 100.0), 2) AS ceiling_incl_gst_per_unit,
       ROUND(100.0 * (c.ceiling_price * (1 + s.value / 100.0) - j.price_per_unit) / (c.ceiling_price * (1 + s.value / 100.0)), 1) AS saving_pct,
       m.method
FROM medicine_matches m
JOIN ja_medicines j ON j.drug_code = m.drug_code
JOIN ceiling_prices c ON c.ceiling_id = m.ceiling_id
JOIN settings s ON s.name = 'gst_percent'
ORDER BY saving_pct DESC;

-- Q5. Data check: any Jan Aushadhi medicine priced ABOVE the ceiling? (usually a wrong match or pack size - check each)
SELECT j.drug_code, j.generic_name, j.unit_size, c.medicine, c.strength, c.unit, m.method
FROM medicine_matches m
JOIN ja_medicines j ON j.drug_code = m.drug_code
JOIN ceiling_prices c ON c.ceiling_id = m.ceiling_id
JOIN settings s ON s.name = 'gst_percent'
WHERE j.price_per_unit > c.ceiling_price * (1 + s.value / 100.0);

-- Q6. Access: Jan Aushadhi Kendras per 1 lakh (100,000) people, by state (lowest first)
SELECT k.state, k.kendras, r.population,
       ROUND(100000.0 * k.kendras / r.population, 2) AS kendras_per_lakh,
       k.as_of, r.pop_source
FROM kendra_counts_state k
JOIN regions r ON r.state = k.state AND r.district = ''
ORDER BY kendras_per_lakh;

-- Q7. Districts with the fewest stores per lakh people (optional: runs only when population.csv also has district rows)
SELECT r.state, r.district, r.population,
       COALESCE(d.kendras, 0) AS kendras,
       ROUND(100000.0 * COALESCE(d.kendras, 0) / r.population, 2) AS kendras_per_lakh
FROM regions r
LEFT JOIN kendra_counts_district d ON d.state = r.state AND d.district = r.district
WHERE r.district <> '' AND EXISTS (SELECT 1 FROM kendra_counts_district)
ORDER BY kendras_per_lakh, r.population DESC
LIMIT 25;
