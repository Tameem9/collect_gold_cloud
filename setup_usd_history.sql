CREATE TABLE IF NOT EXISTS public.usd_egp_history (
    observed_date date PRIMARY KEY,
    collected_at timestamptz NOT NULL,
    provider_updated_at timestamptz,
    usd_egp numeric(14,6) NOT NULL CHECK (usd_egp > 0),
    provider text NOT NULL
);
ALTER TABLE public.usd_egp_history ENABLE ROW LEVEL SECURITY;
GRANT USAGE ON SCHEMA public TO anon, service_role;
GRANT SELECT ON public.usd_egp_history TO anon;
GRANT SELECT, INSERT, UPDATE ON public.usd_egp_history TO service_role;
DROP POLICY IF EXISTS "Public read USD EGP history" ON public.usd_egp_history;
CREATE POLICY "Public read USD EGP history"
ON public.usd_egp_history FOR SELECT TO anon USING (true);
