#include <iostream>
#include <algorithm>

using namespace std;

typedef long long ll;

ll n;

// Helper function to interact with the system
// Terminates program if response is 0 (found solution)
int query(ll x, ll y) {
    if (x > n) x = n;
    if (y > n) y = n;
    cout << x << " " << y << endl;
    int res;
    cin >> res;
    if (res == 0) exit(0);
    return res;
}

ll La = 1, Lb = 1;

// Binary search for b in [low, high] with a fixed assumption for a
void bs_b(ll fixed_a, ll low, ll high) {
    while (low <= high) {
        ll mid = low + (high - low) / 2;
        int r = query(fixed_a, mid);
        if (r == 1) { // fixed_a < a
            // Our assumption that a == fixed_a was wrong, a is larger
            La = fixed_a + 1;
            return;
        } else if (r == 2) { // mid < b
            low = mid + 1;
            Lb = max(Lb, low);
        } else if (r == 3) { // fixed_a > a OR mid > b
            // Since La <= a and fixed_a = La, fixed_a > a is impossible.
            // Thus, it must be mid > b.
            high = mid - 1;
        }
    }
}

// Binary search for a in [low, high] with a fixed assumption for b
void bs_a(ll fixed_b, ll low, ll high) {
    while (low <= high) {
        ll mid = low + (high - low) / 2;
        int r = query(mid, fixed_b);
        if (r == 2) { // fixed_b < b
            // Assumption b == fixed_b was wrong
            Lb = fixed_b + 1;
            return;
        } else if (r == 1) { // mid < a
            low = mid + 1;
            La = max(La, low);
        } else if (r == 3) { // mid > a OR fixed_b > b
            // fixed_b > b is impossible, so mid > a
            high = mid - 1;
        }
    }
}

// Strategy when we suspect a is close to La (or stuck), tries to advance b exponentially
void suspect_a() {
    ll Sb = 1;
    while (La <= n && Lb <= n) {
        ll y = Lb + Sb;
        if (y > n) y = n;
        
        int r = query(La, y);
        if (r == 1) { // La < a
            La = La + 1;
            return; // Back to main strategy
        } else if (r == 2) { // y < b
            Lb = y + 1;
            Sb *= 2;
            if (Sb > n) Sb = n; 
        } else if (r == 3) { // La > a (imp) OR y > b
            // Found upper bound for b
            bs_b(La, Lb, y - 1);
            return;
        }
        if (y == n) break; // Cannot jump further
    }
}

// Strategy when we suspect b is close to Lb (or stuck), tries to advance a exponentially
void suspect_b() {
    ll Sa = 1;
    while (La <= n && Lb <= n) {
        ll x = La + Sa;
        if (x > n) x = n;
        
        int r = query(x, Lb);
        if (r == 2) { // Lb < b
            Lb = Lb + 1;
            return; // Back to main strategy
        } else if (r == 1) { // x < a
            La = x + 1;
            Sa *= 2;
            if (Sa > n) Sa = n;
        } else if (r == 3) { // x > a OR Lb > b (imp)
            // Found upper bound for a
            bs_a(Lb, La, x - 1);
            return;
        }
        if (x == n) break;
    }
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin >> n;
    
    ll S = 1;
    while (La <= n && Lb <= n) {
        ll x = La + S;
        ll y = Lb + S;
        if (x > n) x = n;
        if (y > n) y = n;
        
        int r = query(x, y);
        
        if (r == 1) { // x < a
            La = x + 1;
            S *= 2;
            if (S > n) S = n;
        } else if (r == 2) { // y < b
            Lb = y + 1;
            S *= 2;
            if (S > n) S = n;
        } else if (r == 3) { // x > a OR y > b
            // We overshot, reduce step size
            S /= 2;
            if (S == 0) {
                // Step size reduced to 0, means we are very close to at least one variable.
                // We test the current lower bounds to see which one is "blocking".
                int r2 = query(La, Lb);
                if (r2 == 1) { // La < a
                    La++;
                    suspect_b(); // Suspect b is correct/stuck, try to move a
                    S = 1; 
                } else if (r2 == 2) { // Lb < b
                    Lb++;
                    suspect_a(); // Suspect a is correct/stuck, try to move b
                    S = 1;
                }
                // If r2 == 3, it's impossible (La > a or Lb > b), ignoring as it contradicts invariants.
            }
        }
    }
    return 0;
}