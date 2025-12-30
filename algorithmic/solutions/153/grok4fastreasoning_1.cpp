#include <bits/stdc++.h>
using namespace std;

const int N = 400;
const int M = 1995;
int parent[N];
int rankk[N];

int find(int a) {
    if (parent[a] != a) parent[a] = find(parent[a]);
    return parent[a];
}

void union_sets(int a, int b) {
    a = find(a);
    b = find(b);
    if (a == b) return;
    if (rankk[a] < rankk[b]) swap(a, b);
    parent[b] = a;
    if (rankk[a] == rankk[b]) rankk[a]++;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    vector<int> x(N), y(N);
    for (int i = 0; i < N; i++) {
        cin >> x[i] >> y[i];
    }
    vector<int> U(M), V(M);
    for (int i = 0; i < M; i++) {
        cin >> U[i] >> V[i];
    }
    vector<int> D(M);
    for (int i = 0; i < M; i++) {
        long long dx = x[U[i]] - x[V[i]];
        long long dy = y[U[i]] - y[V[i]];
        double dist = sqrt(dx * dx + dy * dy);
        D[i] = (int)round(dist);
    }
    for (int i = 0; i < N; i++) {
        parent[i] = i;
        rankk[i] = 0;
    }
    for (int i = 0; i < M; i++) {
        int l;
        cin >> l;
        int uu = U[i], vv = V[i];
        int pu = find(uu), pv = find(vv);
        if (pu == pv) {
            cout << 0 << endl;
            continue;
        }
        int min_d = INT_MAX;
        for (int j = i + 1; j < M; j++) {
            int fu = find(U[j]), fv = find(V[j]);
            if ((fu == pu && fv == pv) || (fu == pv && fv == pu)) {
                min_d = min(min_d, D[j]);
            }
        }
        int decision;
        if (min_d == INT_MAX) {
            decision = 1;
        } else {
            if (l <= 3LL * min_d) {
                decision = 1;
            } else {
                decision = 0;
            }
        }
        cout << decision << endl;
        if (decision == 1) {
            union_sets(uu, vv);
        }
    }
    return 0;
}