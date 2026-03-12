import type { Metadata } from 'next'
import { Inter, Playfair_Display } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/lib/auth-context'
import { BrandProvider } from '@/lib/brand-context'
import { Toaster } from 'sonner'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
})

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
})

export const metadata: Metadata = {
  title: 'Arias Conteudo',
  description: 'Plataforma de gestao de conteudo para marcas de musica classica',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="pt-BR" className={`${inter.variable} ${playfair.variable}`}>
      <body className="font-sans antialiased">
        <AuthProvider>
          <BrandProvider>
            {children}
            <Toaster position="top-right" richColors closeButton />
          </BrandProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
