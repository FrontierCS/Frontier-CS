#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Function to perform a query
int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int resp;
    cin >> resp;
    if (resp == -1) exit(0);
    return resp;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    // Shuffle the players to ensure random pairing.
    // This reduces the expected number of queries against an adaptive grader
    // compared to a deterministic order.
    unsigned seed = chrono::system_clock::now().time_since_epoch().count();
    shuffle(p.begin(), p.end(), default_random_engine(seed));

    int impostor = -1;
    // Iterate through pairs. The Impostor will cause a mismatch in responses.
    // Pair (K, K) -> 1, 1 (Same)
    // Pair (Kn, Kn) -> 1, 1 (Same)
    // Pair (K, Kn) -> 0, 0 (Same)
    // Pair (K, I) -> 1, 0 (Different)
    // Pair (Kn, I) -> 0, 1 (Different)
    int limit = n - (n % 2);
    
    for (int k = 0; k < limit; k += 2) {
        int u = p[k];
        int v = p[k+1];

        int r1 = ask(u, v);
        int r2 = ask(v, u);

        if (r1 != r2) {
            // Responses differ => One of u or v is the Impostor.
            // Use a third player w (who is guaranteed not to be the Impostor) as a witness.
            int w;
            if (k + 2 < n) w = p[k+2];
            else w = p[0];

            // Check consistency of u with w.
            // If u is Knight or Knave, ask(u, w) == ask(w, u).
            // If u is Impostor, ask(u, w) != ask(w, u).
            int r_uw = ask(u, w);
            int r_wu = ask(w, u);
            
            if (r_uw != r_wu) {
                impostor = u;
            } else {
                impostor = v;
            }
            break;
        }
    }

    if (impostor == -1) {
        // If no pair triggered a mismatch, the Impostor must be the remaining unpaired player.
        impostor = p[n-1];
    }

    cout << "! " << impostor << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}