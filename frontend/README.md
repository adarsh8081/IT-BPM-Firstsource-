# Frontend - Provider Validation System

Next.js 14 application with TypeScript and Tailwind CSS for the Provider Data Validation & Directory Management System.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## 📁 Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page
├── components/            # React components
│   ├── Dashboard.tsx      # Analytics dashboard
│   ├── ProviderList.tsx   # Provider management
│   ├── ValidationQueue.tsx # Job monitoring
│   └── Settings.tsx       # Configuration
├── lib/                   # Utilities and helpers
├── hooks/                 # Custom React hooks
├── types/                 # TypeScript definitions
└── utils/                 # Utility functions
```

## 🛠️ Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript checks
- `npm run test` - Run tests
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Run tests with coverage

## 🎨 Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Headless UI, Heroicons
- **Forms**: React Hook Form with Zod validation
- **HTTP Client**: Axios
- **Testing**: Jest, React Testing Library

## 🔧 Configuration

### Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Tailwind CSS

The project uses Tailwind CSS with custom configuration in `tailwind.config.js`.

### TypeScript

TypeScript configuration is in `tsconfig.json` with strict type checking enabled.

## 🧪 Testing

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

## 📦 Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

The build output will be in the `.next` directory.