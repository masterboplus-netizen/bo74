-- Миграция 039: расширение связей щит-щит

ALTER TABLE elec_panel_links ADD COLUMN parent_breaker_rating INTEGER;
ALTER TABLE elec_panel_links ADD COLUMN parent_breaker_poles INTEGER;
ALTER TABLE elec_panel_links ADD COLUMN parent_breaker_curve TEXT;
ALTER TABLE elec_panel_links ADD COLUMN child_input_rating INTEGER;
ALTER TABLE elec_panel_links ADD COLUMN is_primary INTEGER DEFAULT 1;
