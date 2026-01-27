#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Wrapper for query to handle interaction and termination checks
int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) {
        exit(0);
    }
    return res;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    // Use a vector of player indices to allow random shuffling
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    // Random shuffle helps in finding the Impostor earlier on average,
    // reducing the total cost (Q).
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    shuffle(p.begin(), p.end(), rng);

    int impostor = -1;
    
    // We process players in pairs (p[k], p[k+1]).
    // Since there is exactly one Impostor, any pair not containing the Impostor
    // will yield symmetric responses (both 0 or both 1).
    // The pair containing the Impostor will yield asymmetric responses (0 and 1).
    
    int limit = n - (n % 2);
    
    for (int k = 0; k < limit; k += 2) {
        int u = p[k];
        int v = p[k+1];

        int r1 = ask(u, v); // u's opinion of v
        int r2 = ask(v, u); // v's opinion of u

        if (r1 != r2) {
            // Found the pair containing the Impostor: {u, v}
            // One is the Impostor, the other is a Knight or Knave.
            // Since we found the Impostor pair, any other player w is NOT the Impostor.
            // We use w as a witness to distinguish between u and v.
            
            int w;
            // Pick a valid witness w != u and w != v
            if (k == 0) {
                // If we are at the first pair, picking from p[2] is safe because n >= 3
                // If n=3, p[2] is the leftover, which is safe since Impostor is in {u, v}
                w = p[2];
            } else {
                // If we are past the first pair, p[0] is safe
                w = p[0];
            }

            int q1 = ask(u, w); // u's opinion of w
            int q2 = ask(v, w); // v's opinion of w

            if (q1 != q2) {
                // Case 1: The pair consists of a Knight and an Impostor.
                // A Knight tells the truth about w.
                // An Impostor lies about w (behaves like a Knave).
                // Since w is not an Impostor, Truth(w) != Lie(w).
                // In the initial pair check {K, I}:
                // K -> I is 1 (Knight sees Impostor as Knight)
                // I -> K is 0 (Impostor sees Knight as Knight, lies -> 0)
                // So the one who said 0 is the Impostor.
                if (r1 == 0) impostor = u;
                else impostor = v;
            } else {
                // Case 2: The pair consists of a Knave and an Impostor.
                // A Knave lies about w.
                // An Impostor lies about w.
                // Lie(w) == Lie(w), so q1 == q2.
                // In the initial pair check {L, I}:
                // L -> I is 0 (Knave sees Impostor as Knight, lies -> 0)
                // I -> L is 1 (Impostor sees Knave as Knave, lies -> 1)
                // So the one who said 1 is the Impostor.
                if (r1 == 1) impostor = u;
                else impostor = v;
            }
            
            cout << "! " << impostor << endl;
            return;
        }
    }

    // If we checked all pairs and found no asymmetry, the Impostor must be the leftover player.
    // This is only possible if n is odd.
    if (n % 2 == 1) {
        cout << "! " << p[n-1] << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}