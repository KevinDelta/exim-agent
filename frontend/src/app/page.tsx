import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold tracking-tight mb-4">
              Compliance Intelligence Platform
            </h1>
            <p className="text-xl text-muted-foreground">
              AI-powered compliance monitoring and advisory services for international trade operations
            </p>
          </div>
          
          <Card className="w-full">
            <CardHeader>
              <CardTitle>Welcome to the Frontend</CardTitle>
              <CardDescription>
                This is the initial setup for the NextJS frontend application. 
                The snapshot card component will be implemented in the next tasks.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">HTS Classification</h3>
                  <p className="text-sm text-muted-foreground">Coming soon...</p>
                </div>
                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">Sanctions Screening</h3>
                  <p className="text-sm text-muted-foreground">Coming soon...</p>
                </div>
                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">Refusal History</h3>
                  <p className="text-sm text-muted-foreground">Coming soon...</p>
                </div>
                <div className="p-4 border rounded-lg">
                  <h3 className="font-semibold mb-2">CBP Rulings</h3>
                  <p className="text-sm text-muted-foreground">Coming soon...</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
