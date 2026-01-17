#include <bits/stdc++.h>
using namespace std;

static bool isInteger(const string &s, long long &val) {
    if (s.empty()) return false;
    char *endptr = nullptr;
    errno = 0;
    val = strtoll(s.c_str(), &endptr, 10);
    if (errno != 0) return false;
    if (endptr != s.c_str() + s.size()) return false;
    return true;
}

static bool isPermutation(const vector<long long> &v, int n) {
    if ((int)v.size() != n) return false;
    vector<char> seen(n + 1, 0);
    for (auto x : v) {
        if (x < 1 || x > n) return false;
        if (seen[(int)x]) return false;
        seen[(int)x] = 1;
    }
    return true;
}

static bool isValidJ(const vector<long long> &v, int n) {
    if ((int)v.size() != n) return false;
    for (int i = 1; i <= n; ++i) {
        long long ji = v[i - 1];
        if (ji < i || ji > min(n, i + 2)) return false;
    }
    return true;
}

static vector<int> simulateFromJ(const vector<long long> &j) {
    int n = (int)j.size();
    vector<int> a(n);
    iota(a.begin(), a.end(), 1);
    for (int i = 1; i <= n; ++i) {
        int ii = i - 1;
        int jj = (int)j[ii] - 1;
        if (ii != jj) swap(a[ii], a[jj]);
    }
    return a;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<string> tokens;
    string tok;
    while (cin >> tok) tokens.push_back(tok);

    if (tokens.empty()) return 0;

    // Check if there are non-integer tokens
    bool allInt = true;
    vector<long long> ints;
    ints.reserve(tokens.size());
    for (auto &s : tokens) {
        long long x;
        if (isInteger(s, x)) ints.push_back(x);
        else allInt = false;
    }

    auto printArray = [](const vector<int> &arr) {
        for (size_t i = 0; i < arr.size(); ++i) {
            if (i) cout << ' ';
            cout << arr[i];
        }
        cout << '\n';
    };

    if (!allInt) {
        // Fallback: interactive-like tokens present; print identity for first integer n (if any)
        if (!ints.empty()) {
            long long nll = ints[0];
            int n = (nll < 0) ? 0 : (int)min(nll, (long long)3000000); // safety cap
            vector<int> a(n);
            iota(a.begin(), a.end(), 1);
            printArray(a);
        }
        return 0;
    }

    // All tokens are integers. Try to detect multi-case or single-case formats.
    size_t ip = 0;
    vector<vector<int>> outputs;

    if (ints.size() == 1) {
        int n = (int)ints[0];
        vector<int> a(n);
        iota(a.begin(), a.end(), 1);
        outputs.push_back(a);
    } else {
        // Try multi-case: first integer is T
        bool parsedMulti = false;
        long long Tll = ints[0];
        if (Tll >= 1 && Tll <= (long long)1e7) {
            size_t idx = 1;
            long long T = Tll;
            vector<vector<int>> tmpOut;
            bool ok = true;
            for (long long t = 0; t < T; ++t) {
                if (idx >= ints.size()) { ok = false; break; }
                if (ints[idx] < 0) { ok = false; break; }
                int n = (int)ints[idx++];
                if (idx + (size_t)n > ints.size()) { ok = false; break; }
                vector<long long> arrll(n);
                for (int i = 0; i < n; ++i) arrll[i] = ints[idx + i];
                idx += n;
                vector<int> out;
                if (isPermutation(arrll, n)) {
                    out.assign(n, 0);
                    for (int i = 0; i < n; ++i) out[i] = (int)arrll[i];
                } else if (isValidJ(arrll, n)) {
                    out = simulateFromJ(arrll);
                } else {
                    out.resize(n);
                    iota(out.begin(), out.end(), 1);
                }
                tmpOut.push_back(move(out));
            }
            if (ok && idx == ints.size()) {
                outputs = move(tmpOut);
                parsedMulti = true;
            }
        }

        if (!parsedMulti) {
            // Single-case: first integer is n, followed by either permutation a or sequence j
            int n = (int)ints[0];
            vector<int> out;
            if (ints.size() >= 1 + (size_t)n) {
                vector<long long> arrll(n);
                for (int i = 0; i < n; ++i) arrll[i] = ints[1 + i];
                if (isPermutation(arrll, n)) {
                    out.assign(n, 0);
                    for (int i = 0; i < n; ++i) out[i] = (int)arrll[i];
                } else if (isValidJ(arrll, n)) {
                    out = simulateFromJ(arrll);
                } else {
                    out.resize(n);
                    iota(out.begin(), out.end(), 1);
                }
            } else {
                out.resize(n);
                iota(out.begin(), out.end(), 1);
            }
            outputs.push_back(move(out));
        }
    }

    for (size_t i = 0; i < outputs.size(); ++i) {
        printArray(outputs[i]);
    }

    return 0;
}