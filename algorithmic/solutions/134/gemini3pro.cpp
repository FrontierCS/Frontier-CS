#include <iostream>
#include <algorithm>

using namespace std;

typedef long long ll;

ll n;
ll La = 1, Lb = 1;

int query(ll x, ll y) {
    if (x > n || y > n) {
        // Treat out of bounds as 'Small' condition response (3) if used in context
        // But normally we shouldn't query out of bounds.
        // Returning 3 is safe for "Is x > a || y > b?" when x > n.
        return 3;
    }
    cout << x << " " << y << endl;
    int res;
    cin >> res;
    if (res == 0) exit(0);
    return res;
}

// Binary search to check if A is Big using range [Lb, Lb + v]
// We are effectively scanning along the line x = La + v.
// Returns 1 if A is Big (found 1 response) or if we infer A Big
// Returns 0 if A is Small
// Side effect: If we find B is Big (response 2), we treat it as just not A Big?
// Actually, if we find B Big, we can technically stop and say B Big.
// But the caller expects status of A.
// However, if B is Big, we might not be able to determine A status easily if interactor spams 2.
// BUT, if B is Big, response 2 is valid. If A is Big, response 1 is valid.
// If A is Small, response 3 is valid (since La+v > a).
// If B is Big, and A is Small, interactor can output 2 or 3.
// If B is Big, and A is Big, interactor can output 1 or 2.
// If interactor outputs 2, we know B is Big.
// If we return special code 2 for B Big, caller can handle.
int solve_bs_a(ll v) {
    ll low = Lb, high = Lb + v;
    if (high > n) high = n;
    
    // Check endpoints
    // We assume low gave 2 in the calling context, but let's be robust.
    // Actually, calling context usually has query(La+v, Lb) == 2.
    
    // Check High
    int r = query(La + v, high);
    if (r == 1) return 1; // A Big
    if (r == 2) return 2; // B Big
    if (r == 3) {
        // We have Low -> 2 (assumed or verified), High -> 3.
        // Search for transition.
        ll L = low, R = high;
        // Invariant: L -> 2 (or 1/3 not seen), R -> 3 (or 1/2 not seen)
        // Actually, strictly: L is "compatible with B Big", R is "compatible with A Small or B Small".
        while (L + 1 < R) {
            ll mid = (L + R) / 2;
            int q = query(La + v, mid);
            if (q == 1) return 1; // A Big
            if (q == 2) L = mid;  // Still B Big candidate
            else R = mid;         // 3 implies A Small or B Small
        }
        // If we exit loop, we have L -> 2, R -> 3.
        // This implies B Big at L (L < b).
        // At R, we have 3.
        // If B was Big at R (R < b), then 2 would be valid.
        // But 3 was chosen. 3 implies La+v > a OR R > b.
        // Since L < b, and R = L+1, b >= R. So R > b is False (unless b=L, but L gives 2 => L < b).
        // So R <= b. Thus R > b is False.
        // Therefore 3 implies La+v > a.
        // So A is Small.
        return 0;
    }
    return 0;
}

// Binary search to check if B is Big using range [La, La + v]
// Scan line y = Lb + v.
// Returns 1 if B Big
// Returns 0 if B Small
// Returns 2 if A Big (Side discovery)
int solve_bs_b(ll v) {
    ll low = La, high = La + v;
    if (high > n) high = n;
    
    int r = query(high, Lb + v);
    if (r == 2) return 1; // B Big
    if (r == 1) return 2; // A Big
    if (r == 3) {
        ll L = low, R = high;
        while (L + 1 < R) {
            ll mid = (L + R) / 2;
            int q = query(mid, Lb + v);
            if (q == 2) return 1; // B Big
            if (q == 1) L = mid;
            else R = mid;
        }
        // L -> 1, R -> 3.
        // L < a. R gives 3.
        // 3 => R > a OR Lb+v > b.
        // Since L < a, a >= L+1 = R. So R > a is False.
        // So Lb+v > b => B Small.
        return 0;
    }
    return 0;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> n)) return 0;
    
    for (int k = 60; k >= 0; --k) {
        ll v = 1LL << k;
        if (La + v > n && Lb + v > n) continue; 
        
        while (true) {
            bool a_can_step = (La + v <= n);
            bool b_can_step = (Lb + v <= n);
            
            if (!a_can_step && !b_can_step) break;
            
            if (!a_can_step) {
                // A is definitely Small w.r.t v (since La+v > n >= a implies La+v > a)
                // Just check B
                int q = query(La, Lb + v);
                if (q == 2) { Lb += v; continue; }
                if (q == 3) break; // B Small
                if (q == 1) {
                    // Interactor evasion. Use BS to force B status.
                    int res = solve_bs_b(v);
                    if (res == 1) { Lb += v; continue; }
                    break; // B Small
                }
            }
            if (!b_can_step) {
                // B is Small. Check A.
                int q = query(La + v, Lb);
                if (q == 1) { La += v; continue; }
                if (q == 3) break; // A Small
                if (q == 2) {
                    int res = solve_bs_a(v);
                    if (res == 1) { La += v; continue; }
                    break; // A Small
                }
            }
            
            // Both can step
            int q1 = query(La + v, Lb + v);
            if (q1 == 1) { La += v; continue; }
            if (q1 == 2) { Lb += v; continue; }
            
            // q1 == 3. At least one is Small.
            // Check A status
            int q2 = query(La + v, Lb);
            if (q2 == 1) { La += v; continue; } // A Big
            if (q2 == 3) {
                // A Small. Need to verify B.
                int q3 = query(La, Lb + v);
                if (q3 == 2) { Lb += v; continue; }
                if (q3 == 3) break; // Both Small
                // q3 == 1. BS B.
                int res = solve_bs_b(v);
                if (res == 1) { Lb += v; continue; }
                break; // B Small
            }
            // q2 == 2. A status ambiguous (B Big possible).
            // Check B status
            int q3 = query(La, Lb + v);
            if (q3 == 2) { Lb += v; continue; }
            if (q3 == 3) {
                // B Small. Need to verify A.
                int res = solve_bs_a(v);
                if (res == 1) { La += v; continue; }
                break; // A Small
            }
            // q3 == 1. Double Deadlock.
            // Resolve A first.
            int resA = solve_bs_a(v);
            if (resA == 1) { La += v; continue; }
            if (resA == 2) { Lb += v; continue; }
            // A Small. Resolve B.
            int resB = solve_bs_b(v);
            if (resB == 1) { Lb += v; continue; }
            // Both Small.
            break;
        }
    }
    
    query(La, Lb);
    
    return 0;
}