"use client"

import { useState, useEffect } from "react"
import { Moon, Sun, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"

export function Header() {
  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
    const isDarkMode = document.documentElement.classList.contains("dark")
    setIsDark(isDarkMode)
  }, [])

  const toggleTheme = () => {
    document.documentElement.classList.toggle("dark")
    setIsDark(!isDark)
  }

  return (
    <header className="border-b bg-card shadow-sm sticky top-0 z-50 backdrop-blur-sm bg-card/95">
      <div className="container mx-auto px-4 lg:px-8 py-4 max-w-7xl">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity group">
            <div className="h-11 w-11 rounded-xl bg-primary flex items-center justify-center shadow-lg group-hover:shadow-xl transition-shadow">
              <Sparkles className="h-6 w-6 text-primary-foreground" />
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-bold leading-tight">Plum Insurance</span>
              <span className="text-xs text-muted-foreground font-medium">OPD Claims Portal</span>
            </div>
          </Link>

          <nav className="flex items-center gap-2">
            <Link href="/">
              <Button variant="ghost" className="text-sm font-semibold">
                Dashboard
              </Button>
            </Link>
            <Link href="/submit">
              <Button variant="ghost" className="text-sm font-semibold">
                Submit Claim
              </Button>
            </Link>
            <div className="h-6 w-px bg-border mx-2" />
            <Button variant="ghost" size="icon" onClick={toggleTheme} className="rounded-full">
              {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>
          </nav>
        </div>
      </div>
    </header>
  )
}
