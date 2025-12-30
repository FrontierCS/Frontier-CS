#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    vector<int> I(M), J(M);
    for (int k = 0; k < M; k++) cin >> I[k] >> J[k];

    int ci = I[0], cj = J[0];
    vector<pair<char,char>> out;

    for (int k = 1; k < M; k++) {
        int ti = I[k], tj = J[k];
        while (ci < ti) { out.push_back({'M','D'}); ci++; }
        while (ci > ti) { out.push_back({'M','U'}); ci--; }
        while (cj < tj) { out.push_back({'M','R'}); cj++; }
        while (cj > tj) { out.push_back({'M','L'}); cj--; }
    }

    for (auto &p : out) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}