#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>

using namespace std;

// Use 128-bit integers for power calculations to avoid overflow.
using int128 = __int128_t;

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    // Choose constants for word length formulas.
    // These are selected to ensure powers are unique for different (u,v) pairs.
    long long C = n + 1;
    long long D = 2 * n + 1;

    // Store lengths for easy access.
    vector<long long> a(n + 1), b(n + 1);
    
    // Generate and print n magic words.
    for (int i = 1; i <= n; ++i) {
        a[i] = C + i;
        b[i] = D + i;
        cout << string(a[i], 'O') + string(b[i], 'X') << "\n";
    }
    cout.flush();

    int q;
    cin >> q;

    // Map to store precomputed powers.
    map<int128, pair<int, int>> power_map;

    // Precompute powers for all n*n pairs.
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            int128 au = a[i], bu = b[i];
            int128 av = a[j], bv = b[j];

            int128 p;
            if (i == j) {
                // Power of a single word O^a X^b.
                p = au + bu + au * bu;
            } else {
                // Power of concatenated word O^au X^bu O^av X^bv.
                // This is calculated by summing counts of unique substring patterns.
                int128 p_o = max(au, av);
                int128 p_x = max(bu, bv);
                int128 p_ox = au * bu + av * bv - min(au, av) * min(bu, bv);
                int128 p_xo = bu * av;
                int128 p_oxo = au * bu * av;
                int128 p_xox = bu * av * bv;
                int128 p_oxox = au * bu * av * bv;

                p = p_o + p_x + p_ox + p_xo + p_oxo + p_xox + p_oxox;
            }
            power_map[p] = {i, j};
        }
    }
    
    // Answer q queries.
    for (int k = 0; k < q; ++k) {
        long long p_ll;
        cin >> p_ll;
        
        // Cast the query power to 128-bit integer for map lookup.
        int128 p_query = p_ll;
        
        pair<int, int> res = power_map[p_query];
        cout << res.first << " " << res.second << "\n";
        cout.flush();
    }

    return 0;
}