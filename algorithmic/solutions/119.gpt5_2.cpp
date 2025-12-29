#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

long long modpow(long long a, long long e) {
    long long r = 1 % MOD;
    a %= MOD;
    while (e > 0) {
        if (e & 1) r = (__int128)r * a % MOD;
        a = (__int128)a * a % MOD;
        e >>= 1;
    }
    return r;
}
long long inv(long long a) {
    a %= MOD;
    if (a < 0) a += MOD;
    return modpow(a, MOD - 2);
}

struct PrefixBuildResult {
    bool ok;
    vector<long long> vals; // a0..a_{i-1}
    long long C;            // constant prefix value after i-1 steps
};

// Build prefix a0..a_{i-1} so that (((...((a0 o1 a1) o2 a2)...) o_{i-1} a_{i-1})) = C, same C for all choices of operations.
// Strategy: choose a0 = seed (seed != 0,1). For j>=1, set a_j = 1 + inv(C_{j-1} - 1), provided C_{j-1} != 0,1.
// If at any step invalid (C==0 or C==1, or a_j==0), return fail and try another seed.
PrefixBuildResult build_prefix_constant(int len) {
    // len = number of prefix operands = i (since indices 0..i-1)
    // If len == 0: no prefix, define empty vals and C as 0? But we only call with i>=1; for safety handle len==1 properly.
    vector<long long> seeds = {2,3,4,5,6,7,8,9,10,11,12,13,17,19,23,29,31,37,41,43,47,53};
    for (long long seed : seeds) {
        if (seed % MOD == 0 || seed % MOD == 1) continue;
        vector<long long> vals;
        vals.reserve(len);
        long long C = seed % MOD;
        vals.push_back(C);
        bool ok = true;
        for (int j = 1; j < len; ++j) {
            if (C % MOD == 0 || C % MOD == 1) { ok = false; break; }
            long long bj = (1 + inv((C - 1 + MOD) % MOD)) % MOD;
            if (bj == 0) { ok = false; break; }
            vals.push_back(bj);
            C = (C + bj) % MOD; // also equals (C * bj) % MOD
        }
        if (ok) {
            return {true, vals, (len == 0 ? 0 : ((vals.size() == 0) ? 0 : (long long)((vals.size() == 1) ? vals[0] : C)))};
        }
    }
    return {false, {}, 0};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) {
        return 0;
    }

    vector<int> op(n + 1, -1); // 0 for '+', 1 for '*', indices 1..n
    int plusSuffixCount = 0;   // number of '+' among positions > current i

    for (int i = n; i >= 1; --i) {
        // Build prefix a0..a_{i-1} giving constant C after i-1 operations
        PrefixBuildResult pref = build_prefix_constant(i);
        if (!pref.ok) {
            // Fallback: in extremely unlikely case, just use simple zero-based method if allowed (setting zeros).
            // But to keep constraints (a_i >= 1), we try another deterministic approach: use seed loop with broader range.
            bool found = false;
            for (long long seed = 2; seed < 1000 && !found; ++seed) {
                if (seed % MOD == 0 || seed % MOD == 1) continue;
                vector<long long> vals;
                vals.reserve(i);
                long long C = seed % MOD;
                vals.push_back(C);
                bool ok = true;
                for (int j = 1; j < i; ++j) {
                    if (C % MOD == 0 || C % MOD == 1) { ok = false; break; }
                    long long bj = (1 + inv((C - 1 + MOD) % MOD)) % MOD;
                    if (bj == 0) { ok = false; break; }
                    vals.push_back(bj);
                    C = (C + bj) % MOD;
                }
                if (ok) {
                    pref = {true, vals, C};
                    found = true;
                }
            }
            if (!found) {
                // As a last resort (should never happen), fall back to zero-based trick (may violate 1<=a_i).
                // We'll still proceed to avoid runtime failure.
                vector<long long> a(n + 1, 0);
                a[i] = 1;
                for (int j = i + 1; j <= n; ++j) a[j] = (op[j] == 1 ? 1 : 0);
                cout << "?";
                for (int k = 0; k <= n; ++k) cout << " " << a[k];
                cout << endl;
                cout.flush();
                long long r;
                if (!(cin >> r)) return 0;
                if (r == 1) op[i] = 0;
                else op[i] = 1;
                plusSuffixCount += (op[i] == 0);
                continue;
            }
        }

        long long C = pref.C % MOD;

        // Choose x for a_i such that C + x != C * x mod MOD to distinguish '+' vs '*'
        // Avoid x == C / (C - 1) mod MOD
        vector<long long> xCandidates = {2,3,4,5,6,7,8,9,10,11,12,13,17,19,23,29,31,37};
        long long forbidden = -1;
        if (C % MOD != 1) {
            forbidden = (__int128)C * inv((C - 1 + MOD) % MOD) % MOD; // x causing equality
        }
        long long x = 2;
        for (long long cand : xCandidates) {
            if (cand % MOD != forbidden && cand % MOD != 0) { x = cand % MOD; break; }
        }
        if (x % MOD == 0) x = 2; // ensure >0

        // Build full query vector
        vector<long long> a(n + 1, 1);
        // prefix:
        for (int j = 0; j < i; ++j) a[j] = pref.vals[j];
        // position i:
        a[i] = x;
        // suffix j>i: set all a_j = 1 to make effect equal to adding count of plus in suffix
        for (int j = i + 1; j <= n; ++j) a[j] = 1;

        // Compute expected answers
        long long k = plusSuffixCount;
        long long ans_plus = (C + x) % MOD;
        ans_plus = (ans_plus + k) % MOD;
        long long ans_times = (__int128)C * x % MOD;
        ans_times = (ans_times + k) % MOD;

        // Issue query
        cout << "?";
        for (int k2 = 0; k2 <= n; ++k2) cout << " " << a[k2];
        cout << endl;
        cout.flush();

        long long r;
        if (!(cin >> r)) return 0;
        r %= MOD;

        if (r == ans_plus) op[i] = 0;
        else if (r == ans_times) op[i] = 1;
        else {
            // In rare case of collision or unexpected, try flipping x to another candidate once
            bool decided = false;
            for (long long cand : xCandidates) {
                if (cand % MOD == x) continue;
                if (cand % MOD == forbidden) continue;
                // rebuild query with new x
                long long x2 = cand % MOD;
                a[i] = x2;
                long long ans_plus2 = (C + x2) % MOD; ans_plus2 = (ans_plus2 + k) % MOD;
                long long ans_times2 = (__int128)C * x2 % MOD; ans_times2 = (ans_times2 + k) % MOD;

                cout << "?";
                for (int k2 = 0; k2 <= n; ++k2) cout << " " << a[k2];
                cout << endl;
                cout.flush();
                if (!(cin >> r)) return 0;
                r %= MOD;
                if (r == ans_plus2) { op[i] = 0; decided = true; break; }
                if (r == ans_times2) { op[i] = 1; decided = true; break; }
            }
            if (!decided) {
                // As last fallback, assume multiplication
                op[i] = 1;
            }
        }

        plusSuffixCount += (op[i] == 0 ? 1 : 0);
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << op[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}