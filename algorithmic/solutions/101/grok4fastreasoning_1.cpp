#include <bits/stdc++.h>
using namespace std;

int N, R, total;
vector<int> lchild, rchild, parentt;
vector<char> typess;

char determine(int tt) {
    vector<int> path;
    int cur = tt;
    while (true) {
        path.push_back(cur);
        if (cur == 0) break;
        cur = parentt[cur];
        if (cur == -1) assert(false); // assume valid tree
    }
    reverse(path.begin(), path.end()); // path[0] = 0, ... path.back() = tt

    vector<char> state(total, '0');

    // Set siblings along the path
    for (size_t i = 0; i + 1 < path.size(); ++i) {
        int gate = path[i];
        int onpath_child = path[i + 1];
        int u = lchild[gate], vv = rchild[gate];
        int sibl = (onpath_child == u ? vv : u);
        char neut = (typess[gate] == '&' ? '1' : '0');
        int dd = neut - '0';
        if (sibl >= N) {
            state[sibl] = neut;
        } else {
            state[sibl] = '0' + dd;
        }
    }

    // Set the test for tt
    int u = lchild[tt], vv = rchild[tt];
    // left to 0
    int d1 = 0;
    if (u >= N) {
        state[u] = '0' + d1;
    } else {
        state[u] = '0' + d1;
    }
    // right to 1
    int d2 = 1;
    if (vv >= N) {
        state[vv] = '0' + d2;
    } else {
        state[vv] = '0' + d2;
    }
    // s[tt] remains '0'

    // Build query string
    string qs = "";
    for (int j = 0; j < total; ++j) {
        qs += state[j];
    }

    // Query
    cout << "? " << qs << endl;
    cout.flush();
    int res;
    cin >> res;
    char typ = (res == 0 ? '&' : '|');
    typess[tt] = typ;
    return typ;
}

void solve(int c) {
    determine(c);
    int u = lchild[c], vv = rchild[c];
    if (u < N) solve(u);
    if (vv < N) solve(vv);
}

int main() {
    cin >> N >> R;
    total = N + R;
    lchild.resize(N);
    rchild.resize(N);
    parentt.assign(total, -1);
    typess.resize(N);
    for (int i = 0; i < N; ++i) {
        int u, v;
        cin >> u >> v;
        lchild[i] = u;
        rchild[i] = v;
        if (parentt[u] != -1 || parentt[v] != -1) {
            // conflict, but assume no
        }
        parentt[u] = i;
        parentt[v] = i;
    }
    parentt[0] = -1; // root
    solve(0);
    string ans = "";
    for (char ch : typess) ans += ch;
    cout << "! " << ans << endl;
    cout.flush();
    return 0;
}