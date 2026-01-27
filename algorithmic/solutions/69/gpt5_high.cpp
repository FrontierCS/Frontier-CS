#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    int limit = 30 * n + 5;
    vector<bool> isPrime(limit + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; 1LL * i * i <= limit; ++i) {
        if (isPrime[i]) {
            for (long long j = 1LL * i * i; j <= limit; j += i) isPrime[(int)j] = false;
        }
    }

    int threshold = 15 * n; // ensure properties discussed
    vector<int> selected;
    selected.reserve(n);
    unordered_set<int> selSet;
    selSet.reserve(n * 2);

    for (int p = 30 * n; p > threshold && (int)selected.size() < n; --p) {
        if (!isPrime[p]) continue;
        if (selSet.count(p + 2)) continue; // avoid twin pairs
        selected.push_back(p);
        selSet.insert(p);
    }
    if ((int)selected.size() < n) {
        for (int p = threshold; p >= 2 && (int)selected.size() < n; --p) {
            if (!isPrime[p]) continue;
            if (selSet.count(p + 2)) continue;
            selected.push_back(p);
            selSet.insert(p);
        }
    }
    if ((int)selected.size() > n) selected.resize(n);

    int p_min = *min_element(selected.begin(), selected.end());
    long long A0 = max(1, p_min - 2);

    vector<long long> U(n), V(n), b(n);
    for (int i = 0; i < n; ++i) {
        long long p = selected[i];
        U[i] = p;           // U_i = p_i
        V[i] = p + 2;       // V_i = p_i + 2
        b[i] = p - A0 - 1;  // b_i = p_i - A0 - 1
        if (b[i] < 1) b[i] = 1; // safety, though should not happen
    }

    unordered_map<long long,int> mapV;
    mapV.reserve(n * 2);
    for (int i = 0; i < n; ++i) mapV[V[i]] = i;

    for (int i = 0; i < n; ++i) {
        string s((size_t)U[i], 'X');
        if (A0 < (long long)s.size()) s[(size_t)A0] = 'O';
        else {
            // fallback if something unexpected (shouldn't happen)
            if (!s.empty()) s.back() = 'O';
        }
        cout << s << "\n";
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;
    while (q--) {
        long long Pj;
        cin >> Pj;
        long long P = Pj + 1; // DS + 1 = U[u] * V[v]
        int u = -1, v = -1;
        for (int i = 0; i < n; ++i) {
            if (P % U[i] == 0) {
                long long valV = P / U[i];
                auto it = mapV.find(valV);
                if (it != mapV.end()) {
                    u = i;
                    v = it->second;
                    break;
                }
            }
        }
        if (u == -1) {
            // Fallback (should never happen)
            for (int j = 0; j < n && u == -1; ++j) {
                if (P % V[j] == 0) {
                    long long valU = P / V[j];
                    for (int i = 0; i < n; ++i) {
                        if (U[i] == valU) { u = i; v = j; break; }
                    }
                }
            }
            if (u == -1) { u = 0; v = 0; }
        }
        cout << (u + 1) << " " << (v + 1) << "\n" << flush;
    }

    return 0;
}