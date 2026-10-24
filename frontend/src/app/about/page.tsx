import { Calculator, Cloud, Database, Gauge, Layers, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

import { SiteHeader } from "@/components/site-header";
import { Ambient } from "@/components/ui";
import { AQI_SCALE, categoryStyle } from "@/lib/format";

function Section({
  icon,
  title,
  index,
  children,
}: {
  icon: ReactNode;
  title: string;
  index: number;
  children: ReactNode;
}) {
  return (
    <section className="card reveal p-5 sm:p-7" style={{ ["--i" as string]: index }}>
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-line bg-surface-2 text-accent">
          {icon}
        </span>
        <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
      </div>
      <div className="mt-4 text-sm leading-7 text-ink/90">{children}</div>
    </section>
  );
}

function Code({ children }: { children: ReactNode }) {
  return (
    <code className="rounded-md border border-line bg-surface-2 px-1.5 py-0.5 font-mono text-[12px] text-ink">
      {children}
    </code>
  );
}

const LIST = "list-disc space-y-2.5 pl-5 marker:text-accent";

export default function AboutPage() {
  return (
    <div className="min-h-screen">
      <Ambient />
      <SiteHeader />
      <main id="main" className="mx-auto max-w-4xl space-y-5 px-4 pb-16 pt-10 sm:px-6 sm:pt-14">
        <header className="reveal pb-4">
          <p className="eyebrow">About</p>
          <h1 className="mt-3 font-display text-5xl leading-[0.98] text-ink sm:text-7xl">About this dashboard</h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted sm:text-lg sm:leading-8">
            Community Air shows local air-quality readings, an Indian AQI when the inputs are valid, and short
            category guidance. It is a public information view, not a medical service.
          </p>
        </header>

        <section className="card reveal p-5 sm:p-7" style={{ ["--i" as string]: 1 }} aria-labelledby="scale-title">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-line bg-surface-2 text-accent">
              <Gauge size={18} />
            </span>
            <div>
              <h2 id="scale-title" className="text-lg font-semibold tracking-tight text-ink">
                The Indian AQI scale
              </h2>
              <p className="text-xs text-muted">Six CPCB bands. The dashboard uses these colours for every AQI value.</p>
            </div>
          </div>
          <ol className="mt-5 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
            {AQI_SCALE.map((band) => {
              const style = categoryStyle(band.category);
              return (
                <li key={band.category} className="overflow-hidden rounded-2xl border border-line bg-surface-2">
                  <div className="h-1.5" style={{ background: style.solid }} />
                  <div className="px-3 py-3">
                    <p className="text-sm font-semibold" style={{ color: style.text }}>
                      {band.category}
                    </p>
                    <p className="mt-0.5 font-mono text-[11px] tabular-nums text-muted">
                      {band.min}–{band.max}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>

        <Section icon={<Calculator size={18} />} title="How Indian AQI is calculated" index={2}>
          <p>
            The backend uses the CPCB National Air Quality Index. Each pollutant gets a sub-index from official
            breakpoints. The overall AQI is the highest valid sub-index. It is calculated only when at least three
            pollutants are valid and one of them is PM2.5 or PM10. PM2.5, PM10, NO2, and SO2 need a 24-hour average
            with at least 16 hours of data. CO and O3 need an 8-hour average with at least 6 hours. If the 8-hour
            ozone average is above 208 µg/m³, the 1-hour ozone value is used instead. Missing numbers are left
            blank. They are never stored or shown as zero.
          </p>
        </Section>

        <Section icon={<Database size={18} />} title="Where the numbers come from" index={3}>
          <ul className={LIST}>
            <li>Station measurements come from OpenAQ. The API key stays on the server.</li>
            <li>
              Until a key is added, the app loads a labeled sample dataset for eight Indian cities so the dashboard
              can be used offline.
            </li>
            <li>Weather and the air-quality forecast come from Open-Meteo. Both are model estimates, not station observations.</li>
            <li>History, comparison, and CSV export read stored rows. They do not call OpenAQ again.</li>
            <li>The map uses OpenStreetMap tiles. Markers are monitoring stations only.</li>
          </ul>
        </Section>

        <Section icon={<Layers size={18} />} title="What this version includes" index={4}>
          <p>
            Search, latest readings, CPCB AQI, health guidance, a filterable station map, date-filtered history,
            city comparison, CSV export, and a separate model forecast. Popular cities can be refreshed by a
            scheduled job. A city with no stored readings is fetched on the first visit. A city whose saved
            readings are older than the cache window is fetched again the next time its dashboard is opened.
            History, comparison, and CSV export keep reading the stored rows.
          </p>
        </Section>

        <Section icon={<Cloud size={18} />} title="Cloud computing design" index={5}>
          <p>
            The API is stateless. Measurements, forecasts, and cache entries live in the database, so a second
            request inside the cache window does not call OpenAQ. When that window has passed, opening the
            dashboard fetches again. If the provider fails, the last stored reading stays on screen and is marked
            stale. The popular-city refresh stays a separate process, which is what Cloud Scheduler will run as a
            Cloud Run job. Google Cloud is the selected host. The OpenAQ key stays in server configuration.
            Deployment has not started, and Cloud SQL stays off until its price is confirmed.
          </p>
          <ul className={`mt-3 ${LIST}`}>
            <li>Compute: Cloud Run for the API and the dashboard.</li>
            <li>
              Scheduled path: popular cities only, as a separate Cloud Run job running <Code>python -m app.jobs.refresh_popular</Code>.
            </li>
            <li>On-demand path: any other city, and any city whose cache window has expired, when its dashboard is opened.</li>
            <li>
              Signals: <Code>/api/v1/health</Code> and <Code>/api/v1/metrics</Code>.
            </li>
            <li>Cost target: $0 inside a verified free tier. No load balancer, NAT gateway, or queue unless one is actually required.</li>
          </ul>
        </Section>

        <Section icon={<TriangleAlert size={18} />} title="Limits" index={6}>
          <ul className={LIST}>
            <li>A city average can hide a dirtier neighbourhood. Check the individual stations.</li>
            <li>If a provider is down, the last stored reading stays on screen and is marked stale.</li>
            <li>Model weather and future air-quality forecasts are not the same thing as a monitor reading.</li>
            <li>Guidance is general. It does not replace advice from a clinician or a local authority.</li>
          </ul>
        </Section>
      </main>
    </div>
  );
}
