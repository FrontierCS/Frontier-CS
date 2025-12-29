#include <bits/stdc++.h>
using namespace std;

using U64 = uint64_t;
const int MAX_POS = 1000;
const int MAX_M = 64;   // we only consider m ≤ 64 for simplicity
int R, H;
int m;                  // number of tests actually used
vector<U64> col(MAX_POS + 1);   // mask for each position (1‑indexed)
unordered_map<U64, pair<int, int>> mp;   // OR mask -> pair of positions

// Try to generate a valid matrix with given m and weight w using random generator gen.
// Returns true if successful.
bool generate(int m, int w, mt19937& gen) {
    vector<int> indices(m);
    iota(indices.begin(), indices.end(), 0);
    set<U64> used;
    for (int p = 1; p <= MAX_POS; ++p) {
        // random permutation of bits, take first w as 1
        shuffle(indices.begin(), indices.end(), gen);
        U64 mask = 0;
        for (int i = 0; i < w; ++i) {
            int bit = indices[i];
            mask |= (U64)1 << bit;
        }
        if (used.count(mask)) {
            return false;   // duplicate column
        }
        used.insert(mask);
        col[p] = mask;
    }

    // Check 2‑separability
    mp.clear();
    for (int i = 1; i <= MAX_POS; ++i) {
        for (int j = i; j <= MAX_POS; ++j) {
            U64 mask = col[i] | col[j];
            if (mp.count(mask)) {
                return false;   // collision found
            }
            mp[mask] = {i, j};
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> R >> H;   // R = 75, H = 1

    // Try to find a valid matrix with as few rows as possible.
    // Start from m = 45 (good balance between score and success probability).
    for (m = 45; m <= MAX_M; ++m) {
        int w = m / 2;   // floor(m/2)
        // Try up to 10 different seeds for this m.
        for (int seed = 0; seed < 10; ++seed) {
            mt19937 gen(seed * 12345 + 6789);
            if (generate(m, w, gen)) {
                goto matrix_found;
            }
        }
    }
    // If we reach here, we failed to generate a matrix with m ≤ 64.
    // This is extremely unlikely; fallback to a trivial (but large) matrix.
    // For completeness we set m = 75 and use the identity idea, but we must
    // ensure correctness. Since probability is negligible, we simply set m = 75
    // and use the same generation loop with more attempts.
    m = 75;
    int w = m / 2;
    for (int seed = 0; seed < 100; ++seed) {
        mt19937 gen(seed * 98765 + 4321);
        if (generate(m, w, gen)) {
            goto matrix_found;
        }
    }
    // Should never happen.
    return 1;

matrix_found:
    // Send all queries corresponding to the rows of the matrix.
    for (int r = 0; r < m; ++r) {
        vector<int> positions;
        for (int p = 1; p <= MAX_POS; ++p) {
            if ((col[p] >> r) & 1) {
                positions.push_back(p);
            }
        }
        cout << "? " << positions.size();
        for (int pos : positions) {
            cout << " " << pos;
        }
        cout << endl;
        cout.flush();
    }

    // Wait one hour and get the results.
    cout << "@" << endl;
    cout.flush();

    int L;
    cin >> L;
    U64 result_mask = 0;
    for (int i = 0; i < L; ++i) {
        int bit;
        cin >> bit;
        if (bit) {
            result_mask |= (U64)1 << i;
        }
    }

    // Look up the pair that produced this OR mask.
    auto it = mp.find(result_mask);
    if (it != mp.end()) {
        int a = it->second.first;
        int b = it->second.second;
        cout << "! " << a << " " << b << endl;
    } else {
        // This should never happen with a valid matrix.
        // Fallback output (guaranteed to be wrong, but keeps the program running).
        cout << "! 1 1" << endl;
    }
    cout.flush();

    return 0;
}