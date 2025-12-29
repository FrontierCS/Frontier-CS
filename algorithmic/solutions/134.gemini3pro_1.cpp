#include <iostream>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

typedef long long ll;

ll query(ll x, ll y) {
    cout << x << " " << y << endl;
    ll ans;
    cin >> ans;
    if (ans == 0) exit(0);
    return ans;
}

int main() {
    ll n;
    if (!(cin >> n)) return 0;

    ll La = 1, Ra = n;
    ll Lb = 1, Rb = n;

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    while (La <= Ra && Lb <= Rb) {
        // Pick midpoints. Using randomization to break adversarial loops.
        // We bias towards the center to ensure logarithmic reduction on average.
        ll ma = La + (Ra - La) / 2;
        ll mb = Lb + (Rb - Lb) / 2;
        
        // Add some noise, but keep within bounds
        if (La < Ra) {
             ll range = Ra - La;
             ll noise = (ll)(rng() % (range / 2 + 1)) - range / 4;
             ma = max(La, min(Ra, ma + noise));
        }
        if (Lb < Rb) {
             ll range = Rb - Lb;
             ll noise = (ll)(rng() % (range / 2 + 1)) - range / 4;
             mb = max(Lb, min(Rb, mb + noise));
        }

        // 1. Main Query
        ll ans1 = query(ma, mb);
        if (ans1 == 1) {
            La = ma + 1;
            continue;
        }
        if (ans1 == 2) {
            Lb = mb + 1;
            continue;
        }
        // ans1 == 3: a < ma OR b < mb
        
        // 2. Try to verify a < ma using Lb
        ll ans2 = query(ma, Lb);
        if (ans2 == 1) { // ma < a
            // Contradicts a < ma, so b < mb must be true
            // Also we learned a > ma
            La = ma + 1;
            Rb = mb - 1;
            continue;
        }
        if (ans2 == 3) { // ma > a (since Lb > b impossible)
            Ra = ma - 1;
            continue;
        }
        // ans2 == 2: Lb < b. Evasion. We learned b > Lb.
        
        // 3. Try to verify b < mb using La
        ll ans3 = query(La, mb);
        if (ans3 == 2) { // mb < b
            // Contradicts b < mb, so a < ma must be true
            // Also we learned b > mb
            Ra = ma - 1;
            Lb = mb + 1;
            continue;
        }
        if (ans3 == 3) { // mb > b (since La > a impossible)
            Rb = mb - 1;
            continue;
        }
        // ans3 == 1: La < a. Evasion. We learned a > La.

        // If we reach here, we have Double Evasion: b > Lb AND a > La.
        // And we still have the ambiguity from ans1 (a < ma OR b < mb).
        // Try to verify using upper bounds.
        
        // 4. Try to verify using Rb
        ll ans4 = query(ma, Rb);
        if (ans4 == 1) { // ma < a
            // Implies b < mb (from ans1)
            La = ma + 1;
            Rb = mb - 1;
            continue;
        }
        // ans4 == 3: ma > a OR Rb > b
        // If Rb is tight, then ma > a. If Rb loose, ambiguous.

        // 5. Try to verify using Ra
        ll ans5 = query(Ra, mb);
        if (ans5 == 2) { // mb < b
             // Implies a < ma (from ans1)
             Ra = ma - 1;
             Lb = mb + 1;
             continue;
        }
        // ans5 == 3: Ra > a OR mb > b
        
        // If we reach here, we are fully stuck in this iteration.
        // We know:
        // ans1=3 => (a < ma OR b < mb)
        // ans2=2 => b > Lb
        // ans3=1 => a > La
        // ans4=3 => (a < ma OR b < Rb) -- likely a < ma if Rb tight
        // ans5=3 => (a < Ra OR b < mb) -- likely b < mb if Ra tight
        
        // We update the lower bounds because we are certain a > La and b > Lb.
        La++;
        Lb++;
        
        // We DO NOT update upper bounds because we are not certain.
        // We continue the loop. The randomization of midpoints in next iter 
        // will likely break the ambiguity.
    }

    return 0;
}