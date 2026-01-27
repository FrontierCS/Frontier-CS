#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<vector<char>> Dist(n, vector<char>(n));
    for (int i = 0; i < n; i++) for (int j = 0; j < n; j++) cin >> Dist[i][j];
    vector<vector<char>> Flow(n, vector<char>(n));
    for (int i = 0; i < n; i++) for (int j = 0; j < n; j++) cin >> Flow[i][j];
    vector<int> degF(n, 0), degD(n, 0);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            degF[i] += Flow[i][j];
            degD[i] += Dist[i][j];
        }
    }
    vector<int> fac(n);
    iota(fac.begin(), fac.end(), 0);
    sort(fac.begin(), fac.end(), [&](int x, int y) {
        if (degF[x] != degF[y]) return degF[x] > degF[y];
        return x < y;
    });
    vector<int> locs(n);
    iota(locs.begin(), locs.end(), 0);
    sort(locs.begin(), locs.end(), [&](int x, int y) {
        if (degD[x] != degD[y]) return degD[x] < degD[y];
        return x < y;
    });
    vector<int> pos(n);
    for (int i = 0; i < n; i++) {
        pos[fac[i]] = locs[i];
    }
    srand(time(NULL));
    const int MAX_ITER = 100000;
    for (int iter = 0; iter < MAX_ITER; iter++) {
        int x = rand() % n;
        int y = rand() % n;
        while (y == x) y = rand() % n;
        int a = pos[x], b = pos[y];
        long long delta = 0;
        for (int k = 0; k < n; k++) {
            if (k == x || k == y) continue;
            int pk = pos[k];
            delta += (long long)Flow[x][k] * (Dist[b][pk] - Dist[a][pk]);
            delta += (long long)Flow[y][k] * (Dist[a][pk] - Dist[b][pk]);
            delta += (long long)Flow[k][x] * (Dist[pk][b] - Dist[pk][a]);
            delta += (long long)Flow[k][y] * (Dist[pk][a] - Dist[pk][b]);
        }
        delta += (long long)Flow[x][x] * (Dist[b][b] - Dist[a][a]);
        delta += (long long)Flow[y][y] * (Dist[a][a] - Dist[b][b]);
        delta += (long long)Flow[x][y] * (Dist[b][a] - Dist[a][b]);
        delta += (long long)Flow[y][x] * (Dist[a][b] - Dist[b][a]);
        if (delta < 0) {
            swap(pos[x], pos[y]);
        }
    }
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << pos[i] + 1;
    }
    cout << endl;
    return 0;
}