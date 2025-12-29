#include <bits/stdc++.h>
using namespace std;

static int n;
static int A, B;
static int queries = 0;

pair<int,int> query_except(int i, int j) {
    vector<int> idx;
    idx.reserve(n - 2);
    for (int t = 1; t <= n; t++) {
        if (t == i || t == j) continue;
        idx.push_back(t);
    }
    int k = (int)idx.size();
    cout << 0 << ' ' << k;
    for (int x : idx) cout << ' ' << x;
    cout << '\n';
    cout.flush();
    queries++;

    int m1, m2;
    if (!(cin >> m1 >> m2)) exit(0);
    if (m1 == -1 && m2 == -1) exit(0);
    return {m1, m2};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    A = n / 2;
    B = A + 1;

    int x = -1, y = -1;

    // Find a balanced pair (x,y) such that excluding them yields (A,B)
    for (int base = 1; base <= n && x == -1; base++) {
        for (int j = 1; j <= n; j++) {
            if (j == base) continue;
            auto res = query_except(base, j);
            if (res.first == A && res.second == B) {
                x = base;
                y = j;
                break;
            }
            if (queries >= 500) exit(0);
        }
    }

    if (x == -1) exit(0);

    int idxA = -1, idxB = -1;

    // Determine orientation and find one of the medians using anchor x
    for (int i = 1; i <= n; i++) {
        if (i == x || i == y) continue;
        auto res = query_except(x, i);
        if (res.first == A - 1 && res.second == B) { // x is high, i is A
            idxA = i;
            break;
        }
        if (res.first == A && res.second == B + 1) { // x is low, i is B
            idxB = i;
            break;
        }
        if (queries >= 500) exit(0);
    }

    if (idxA != -1) {
        // x is high => y is low, find B using y
        for (int i = 1; i <= n; i++) {
            if (i == x || i == y || i == idxA) continue;
            auto res = query_except(y, i);
            if (res.first == A && res.second == B + 1) {
                idxB = i;
                break;
            }
            if (queries >= 500) exit(0);
        }
    } else if (idxB != -1) {
        // x is low => y is high, find A using y
        for (int i = 1; i <= n; i++) {
            if (i == x || i == y || i == idxB) continue;
            auto res = query_except(y, i);
            if (res.first == A - 1 && res.second == B) {
                idxA = i;
                break;
            }
            if (queries >= 500) exit(0);
        }
    } else {
        exit(0);
    }

    if (idxA == -1 || idxB == -1) exit(0);

    cout << 1 << ' ' << idxA << ' ' << idxB << '\n';
    cout.flush();
    return 0;
}