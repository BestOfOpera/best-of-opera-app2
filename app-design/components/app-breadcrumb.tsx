interface AppBreadcrumbProps { items: string[] }

export function AppBreadcrumb({ items }: AppBreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-muted-foreground/40">/</span>}
          <span className={i === items.length - 1 ? "font-medium text-foreground" : "text-muted-foreground"}>{item}</span>
        </span>
      ))}
    </nav>
  )
}
