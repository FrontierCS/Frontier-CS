#include <bits/stdc++.h>
using namespace std;

static int adjMat[101][101];

static int ask(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl; // endl flushes
    int x;
    if (!(cin >> x)) exit(0);
    if (x < 0) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 100;

    // Reconstruct induced subgraph on vertices 1..5 by querying all triples (10 queries)
    vector<array<int,3>> triples;
    for (int i = 1; i <= 5; i++)
        for (int j = i + 1; j <= 5; j++)
            for (int k = j + 1; k <= 5; k++)
                triples.push_back({i,j,k});

    vector<int> triAns(triples.size());
    for (size_t t = 0; t < triples.size(); t++) {
        triAns[t] = ask(triples[t][0], triples[t][1], triples[t][2]);
    }

    int idx[6][6];
    memset(idx, -1, sizeof(idx));
    vector<pair<int,int>> edges;
    for (int i = 1; i <= 5; i++) {
        for (int j = i + 1; j <= 5; j++) {
            idx[i][j] = idx[j][i] = (int)edges.size();
            edges.push_back({i,j});
        }
    }

    int foundMask = -1;
    for (int mask = 0; mask < (1 << (int)edges.size()); mask++) {
        bool ok = true;
        for (size_t t = 0; t < triples.size(); t++) {
            int a = triples[t][0], b = triples[t][1], c = triples[t][2];
            int eab = (mask >> idx[a][b]) & 1;
            int eac = (mask >> idx[a][c]) & 1;
            int ebc = (mask >> idx[b][c]) & 1;
            int s = eab + eac + ebc;
            if (s != triAns[t]) { ok = false; break; }
        }
        if (ok) { foundMask = mask; break; }
    }
    if (foundMask == -1) return 0;

    for (int i = 1; i <= 5; i++) {
        for (int j = i + 1; j <= 5; j++) {
            int val = (foundMask >> idx[i][j]) & 1;
            adjMat[i][j] = adjMat[j][i] = val;
        }
    }

    // Incrementally add vertices 6..100 using pivot vertex 1
    for (int v = 6; v <= N; v++) {
        int k = v - 1;
        vector<int> t(k + 1, -1); // t[i] = adj(v,1) + adj(v,i)

        for (int i = 2; i <= k; i++) {
            int ans = ask(v, 1, i);
            t[i] = ans - adjMat[1][i];
        }

        int d1 = -1; // adj(v,1)
        for (int i = 2; i <= k; i++) {
            if (t[i] == 0) d1 = 0;
            else if (t[i] == 2) d1 = 1;
        }

        if (d1 == -1) {
            // all t[i] == 1
            int ans = ask(v, 2, 3);
            int s = ans - adjMat[2][3]; // = adj(v,2) + adj(v,3)
            // If d1=1 then adj(v,2)=adj(v,3)=0 => s=0; else s=2
            d1 = (s == 0 ? 1 : 0);
        }

        adjMat[v][1] = adjMat[1][v] = d1;
        for (int i = 2; i <= k; i++) {
            int di = t[i] - d1;
            adjMat[v][i] = adjMat[i][v] = di;
        }
    }

    cout << "!" << endl;
    for (int i = 1; i <= N; i++) {
        string s;
        s.reserve(N);
        for (int j = 1; j <= N; j++) {
            if (i == j) s.push_back('0');
            else s.push_back(adjMat[i][j] ? '1' : '0');
        }
        cout << s << endl;
    }
    cout.flush();
    return 0;
}