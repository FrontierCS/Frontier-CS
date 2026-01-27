#include <bits/stdc++.h>
using namespace std;

int t, n;
map<pair<int, int>, int> cache;

int ask(int i, int j) {
    if (i == j) return -1; // should never happen
    if (cache.count({i, j})) return cache[{i, j}];
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int ans;
    cin >> ans;
    if (ans == -1) exit(0); // invalid response, terminate
    cache[{i, j}] = ans;
    return ans;
}

void solve() {
    cache.clear();
    cin >> n;
    vector<int> group(n + 1, -1); // 0 = same type as player 1, 1 = different
    group[1] = 0;
    vector<int> X(n + 1, -1);    // X[i] = answer of player 1 about i
    int imp = -1;

    for (int i = 2; i <= n; ++i) {
        int j;
        if (i != 2) j = 2;
        else j = 3;                     // for i=2 we use j=3 to avoid i=j
        int a1j = ask(1, j);
        int aij = ask(i, j);
        int diff = a1j ^ aij;
        group[i] = diff;

        X[i] = ask(1, i);              // compute X[i]

        // early detection of impostor
        if (group[i] == 0 && X[i] == 0) {
            imp = i;
            break;
        }
        if (group[i] == 1 && X[i] == 1) {
            imp = i;
            break;
        }
    }

    if (imp != -1) {
        cout << "! " << imp << endl;
        cout.flush();
        return;
    }

    // find any player of different type than player 1
    int t = -1;
    for (int i = 2; i <= n; ++i) {
        if (group[i] == 1) {
            t = i;
            break;
        }
    }
    // t must exist (because there is at least one knave)
    int at1 = ask(t, 1);
    X[1] = 1 - at1;                    // derive X[1]

    if (group[1] == 0 && X[1] == 0) imp = 1;
    else if (group[1] == 1 && X[1] == 1) imp = 1;

    cout << "! " << imp << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}