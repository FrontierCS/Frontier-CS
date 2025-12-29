#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    if (n == 1) {
        cout << 1 << " " << 1 << endl;
        cout.flush();
        return 0;
    }
    vector<int> base(n + 1);
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    bool found_base = false;
    int tries = 0;
    while (!found_base && tries < 100) {
        vector<int> cand(n);
        iota(cand.begin(), cand.end(), 1);
        shuffle(cand.begin(), cand.end(), rng);
        cout << 0;
        for (int v : cand) cout << " " << v;
        cout << endl;
        cout.flush();
        int x;
        cin >> x;
        if (x == 0) {
            found_base = true;
            for (int i = 1; i <= n; i++) base[i] = cand[i - 1];
        }
        tries++;
    }
    // Assume found, as probability is high
    vector<int> permutation(n + 1, 0);
    int known_count = 0;
    for (int val = 1; val <= n; val++) {
        vector<int> possible;
        for (int i = 1; i <= n; i++) {
            if (permutation[i] == 0) possible.push_back(i);
        }
        int l = 0, r = possible.size() - 1;
        while (l < r) {
            int m = (l + r) / 2;
            vector<int> S;
            for (int k = l; k <= m; k++) S.push_back(possible[k]);
            vector<int> Q(n + 1);
            for (int i = 1; i <= n; i++) Q[i] = base[i];
            for (int posi : S) Q[posi] = val;
            cout << 0;
            for (int i = 1; i <= n; i++) cout << " " << Q[i];
            cout << endl;
            cout.flush();
            int x;
            cin >> x;
            int ind = x - known_count;
            if (ind == 1) {
                r = m;
            } else {
                l = m + 1;
            }
        }
        int posi = possible[l];
        permutation[posi] = val;
        base[posi] = val;
        known_count++;
    }
    cout << 1;
    for (int i = 1; i <= n; i++) cout << " " << permutation[i];
    cout << endl;
    cout.flush();
    return 0;
}