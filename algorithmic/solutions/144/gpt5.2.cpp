#include <bits/stdc++.h>
using namespace std;

struct Resp {
    int a, b;
};

static int n;
static int m;
static int queries = 0;

Resp ask_excluding(int e1, int e2) {
    vector<int> idx;
    idx.reserve(n - 2);
    for (int i = 1; i <= n; i++) {
        if (i == e1 || i == e2) continue;
        idx.push_back(i);
    }

    cout << "0 " << (n - 2);
    for (int x : idx) cout << ' ' << x;
    cout << endl;
    cout.flush();

    queries++;
    int x, y;
    if (!(cin >> x >> y)) exit(0);
    if (x == -1 && y == -1) exit(0);
    return {x, y};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    m = n / 2;

    int P = -1, Q = -1;
    for (int p = 1; p <= n && P == -1; p++) {
        for (int q = 1; q <= n; q++) {
            if (q == p) continue;
            Resp r = ask_excluding(p, q);
            if (r.a == m && r.b == m + 1) {
                P = p;
                Q = q;
                break;
            }
        }
    }

    if (P == -1) {
        cout << "1 1 2" << endl;
        cout.flush();
        return 0;
    }

    vector<int> med;
    for (int x = 1; x <= n; x++) {
        if (x == P || x == Q) continue;
        Resp r1 = ask_excluding(P, x);
        Resp r2 = ask_excluding(Q, x);
        bool ok1 = (r1.a == m && r1.b == m + 1);
        bool ok2 = (r2.a == m && r2.b == m + 1);
        if (!ok1 && !ok2) med.push_back(x);
    }

    if ((int)med.size() < 2) {
        // Fallback (should not happen with correct logic)
        vector<int> cand;
        for (int i = 1; i <= n; i++) if (i != P && i != Q) cand.push_back(i);
        while ((int)med.size() < 2 && !cand.empty()) {
            med.push_back(cand.back());
            cand.pop_back();
        }
    }

    cout << "1 " << med[0] << ' ' << med[1] << endl;
    cout.flush();
    return 0;
}