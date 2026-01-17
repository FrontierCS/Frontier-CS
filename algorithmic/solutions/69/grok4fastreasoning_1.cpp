#include <bits/stdc++.h>
using namespace std;

long long compute_power(long long bu, long long bv) {
    long long mx = max(bu, bv);
    return 1LL + 2 * mx + 2 * bu + 2 * bu * bv;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<int> bb(n + 1);
    set<long long> used;
    map<long long, pair<int, int>> lookup;
    bb[1] = 1;
    long long p11 = compute_power(1, 1);
    used.insert(p11);
    lookup[p11] = {1, 1};
    for (int i = 2; i <= n; ++i) {
        int cand = bb[i - 1] + 1;
        while (true) {
            set<long long> newp;
            bool good = true;
            for (int j = 1; j <= i; ++j) {
                long long pji = compute_power(bb[j], cand);
                if (used.count(pji) || newp.count(pji)) {
                    good = false;
                    break;
                }
                newp.insert(pji);
                if (j < i) {
                    long long pij = compute_power(cand, bb[j]);
                    if (used.count(pij) || newp.count(pij)) {
                        good = false;
                        break;
                    }
                    newp.insert(pij);
                }
            }
            if (good) {
                bb[i] = cand;
                for (auto pp : newp) {
                    used.insert(pp);
                }
                for (int j = 1; j <= i; ++j) {
                    long long pji = compute_power(bb[j], cand);
                    lookup[pji] = {j, i};
                    if (j < i) {
                        long long pij = compute_power(cand, bb[j]);
                        lookup[pij] = {i, j};
                    }
                }
                break;
            }
            ++cand;
            if (cand > 30 * n) {
                assert(false); // Should not happen
            }
        }
    }
    for (int i = 1; i <= n; ++i) {
        string wi(1, 'O');
        wi += string(bb[i], 'X');
        cout << wi << '\n';
    }
    cout << flush;
    int q;
    cin >> q;
    for (int qq = 0; qq < q; ++qq) {
        long long p;
        cin >> p;
        auto [u, v] = lookup[p];
        cout << u << " " << v << '\n';
        cout << flush;
    }
    return 0;
}