#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <set>

using namespace std;

// Function to calculate the number of distinct substrings of X^A O X^B O X^C
// The concatenation of w_u (X^a O X^b) and w_v (X^c O X^d) results in
// X^a O X^(b+c) O X^d.
// Let A = a, B = b + c, C = d.
long long calc_power(long long A, long long B, long long C) {
    long long term1 = max({A, B, C});
    long long term2 = (A + 1) * (B + 1);
    long long term3 = (B + 1) * (C + 1);
    long long min_ab = min(A, B);
    long long min_bc = min(B, C);
    long long term4 = (min_ab + 1) * (min_bc + 1);
    long long term5 = (A + 1) * (C + 1);
    return term1 + term2 + term3 - term4 + term5;
}

// Global storage for powers to indices mapping
map<long long, pair<int, int>> power_map;

struct Word {
    long long a, b;
};
vector<Word> words;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    words.reserve(n);
    set<pair<long long, long long>> used_words;
    
    long long next_a = 1;

    for (int k = 1; k <= n; ++k) {
        bool found = false;
        // Search for valid (a, b)
        // We iterate 'a' starting from next_a to preserve monotonicity and speed up search
        // 'b' is kept small to minimize word length
        for (long long a = next_a; a <= 30000; ++a) {
            for (long long b = 1; b <= 5; ++b) {
                if (used_words.count({a, b})) continue;

                // We need to check if adding this word creates any collision in power values.
                // New pairs formed are: (i, k) and (k, i) for all 1 <= i <= k.
                // Specifically for vector indices 0..k-1 (where new word is at k-1).
                
                vector<pair<long long, pair<int, int>>> new_entries;
                new_entries.reserve(2 * k);
                bool ok = true;

                // 1. Self pair (k, k) -> w_k + w_k
                // Form: X^a O X^b + X^a O X^b = X^a O X^(b+a) O X^b
                long long p_self = calc_power(a, b + a, b);
                if (power_map.count(p_self)) { ok = false; }
                else {
                    new_entries.push_back({p_self, {k, k}});
                }

                if (!ok) continue;

                // 2. Pairs with existing words
                for (int i = 0; i < k - 1; ++i) {
                    // Pair (i+1, k): words[i] then current(a,b)
                    // words[i] = X^A1 O X^B1
                    // current = X^a O X^b
                    // Concat: X^A1 O X^(B1+a) O X^b
                    long long p1 = calc_power(words[i].a, words[i].b + a, b);
                    if (power_map.count(p1)) { ok = false; break; }
                    // Check against new_entries
                    for (const auto& entry : new_entries) if (entry.first == p1) { ok = false; break; }
                    if (!ok) break;
                    new_entries.push_back({p1, {i + 1, k}});

                    // Pair (k, i+1): current(a,b) then words[i]
                    // Concat: X^a O X^(b + A1) O X^B1
                    long long p2 = calc_power(a, b + words[i].a, words[i].b);
                    if (power_map.count(p2)) { ok = false; break; }
                    // Check against new_entries
                    for (const auto& entry : new_entries) if (entry.first == p2) { ok = false; break; }
                    if (!ok) break;
                    new_entries.push_back({p2, {k, i + 1}});
                }

                if (ok) {
                    // Valid word found
                    words.push_back({a, b});
                    used_words.insert({a, b});
                    for (const auto& entry : new_entries) {
                        power_map[entry.first] = entry.second;
                    }
                    next_a = a; 
                    found = true;
                    break;
                }
            }
            if (found) break;
        }
    }

    // Output words
    for (const auto& w : words) {
        string s;
        s.reserve(w.a + 1 + w.b);
        s.append(w.a, 'X');
        s += 'O';
        s.append(w.b, 'X');
        cout << s << "\n";
    }
    cout << flush;

    // Handle queries
    int q;
    if (cin >> q) {
        for (int j = 0; j < q; ++j) {
            long long pj;
            cin >> pj;
            if (power_map.find(pj) != power_map.end()) {
                pair<int, int> res = power_map[pj];
                cout << res.first << " " << res.second << endl;
            } else {
                // Fallback, though guaranteed to exist
                cout << "1 1" << endl;
            }
        }
    }

    return 0;
}