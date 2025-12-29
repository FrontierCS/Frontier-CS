#include <bits/stdc++.h>
using namespace std;

// Interactive solver using Kautz-Singleton (Reed–Solomon based) 2-disjunct code.
// Parameters chosen: q = 13 (prime), k = 3, n = k + d = 5 with d = 2 (can decode up to 2 positives).
// Tests: L = n * q = 65 <= R=75.
//
// Query format (per problem statement):
// - Send robot: "? k p1 p2 ... pk"
// - Get answers: print "@" then read L followed by L integers (0/1)
// - Output result: "! a b"

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) {
        return 0;
    }

    const int N = 1000;
    const int q = 13;      // field size
    const int k = 3;       // message length (polynomial degree < k)
    const int n = 5;       // number of evaluation points
    const int L = n * q;   // total number of tests (rows)

    // Precompute evaluation values f_x(alpha_i) for each position x in [1..1000], i in [0..n-1]
    // Map x-1 to coefficients (a0, a1, a2) in base-q (q=13)
    vector<array<int, n>> fx(N + 1);
    for (int x = 1; x <= N; ++x) {
        int idx = x - 1;
        int a0 = idx % q;
        int a1 = (idx / q) % q;
        int a2 = (idx / (q * q)) % q;
        for (int i = 0; i < n; ++i) {
            int t = i % q;
            int t2 = (t * t) % q;
            int val = (a0 + a1 * t + a2 * t2) % q;
            fx[x][i] = val;
        }
    }

    // Prepare the 65 subsets S_{i,s} = { x | f_x(alpha_i) == s }
    vector<vector<int>> queries;
    queries.reserve(L);
    for (int i = 0; i < n; ++i) {
        for (int s = 0; s < q; ++s) {
            vector<int> subset;
            subset.reserve(N / q + 5);
            for (int x = 1; x <= N; ++x) {
                if (fx[x][i] == s) subset.push_back(x);
            }
            queries.push_back(move(subset));
        }
    }

    // Send all queries
    for (const auto &subset : queries) {
        cout << "? " << subset.size();
        for (int v : subset) cout << ' ' << v;
        cout << '\n';
        cout.flush();
    }

    // Request answers
    cout << "@\n";
    cout.flush();

    int Lret;
    if (!(cin >> Lret)) {
        // Fallback if no interaction available
        cout << "! 1 1\n";
        cout.flush();
        return 0;
    }
    vector<int> ans(Lret);
    for (int i = 0; i < Lret; ++i) cin >> ans[i];

    // Build codewords for all positions: bitset of length L.
    // Row index mapping: r = i * q + s
    const int MAXL = 80;
    vector<bitset<MAXL>> code(N + 1);
    for (int x = 1; x <= N; ++x) {
        bitset<MAXL> b;
        for (int i = 0; i < n; ++i) {
            int s = fx[x][i];
            int r = i * q + s;
            b.set(r);
        }
        code[x] = b;
    }

    // Build observed result vector y
    bitset<MAXL> y;
    for (int r = 0; r < Lret && r < L; ++r) {
        if (ans[r]) y.set(r);
    }

    // Eliminate candidates: For 2-disjunct code, survivors equal positives
    vector<int> survivors;
    survivors.reserve(2);
    for (int x = 1; x <= N; ++x) {
        bitset<MAXL> bx = code[x];
        // If bx has any 1 in a position where y is 0, it's impossible
        if ((bx & (~y)).any()) continue;
        survivors.push_back(x);
    }

    int a = 1, b = 1;
    if (survivors.size() == 2) {
        a = survivors[0];
        b = survivors[1];
    } else if (survivors.size() == 1) {
        a = b = survivors[0];
    } else if (survivors.size() > 2) {
        // Try to find a pair whose OR equals y
        bool found = false;
        for (size_t i = 0; i < survivors.size() && !found; ++i) {
            for (size_t j = i; j < survivors.size(); ++j) {
                if ((code[survivors[i]] | code[survivors[j]]) == y) {
                    a = survivors[i];
                    b = survivors[j];
                    found = true;
                    break;
                }
            }
        }
        if (!found) {
            a = survivors[0];
            b = survivors[1];
        }
    } else {
        // No survivors due to unexpected input; choose defaults
        a = b = 1;
    }

    cout << "! " << a << ' ' << b << '\n';
    cout.flush();

    return 0;
}