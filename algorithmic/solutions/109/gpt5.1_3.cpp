#include <bits/stdc++.h>
using namespace std;

struct Item {
    unsigned char d;
    int v;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int rs, cs;
    cin >> rs >> cs;
    --rs; --cs;

    int total = N * N;

    vector<array<int, 8>> nb(total);
    vector<unsigned char> nbCount(total);

    const int dr[8] = {2, 1, -1, -2, -2, -1, 1, 2};
    const int dc[8] = {1, 2,  2,  1, -1, -2,-2,-1};

    auto id = [N](int r, int c) { return r * N + c; };

    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int u = id(r, c);
            unsigned char cnt = 0;
            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k], nc = c + dc[k];
                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    nb[u][cnt++] = id(nr, nc);
                }
            }
            nbCount[u] = cnt;
        }
    }

    vector<unsigned char> visited(total);
    vector<unsigned char> degLeft(total);

    vector<int> path;
    path.reserve(total);
    vector<int> bestPath;
    bestPath.reserve(total);

    int start = id(rs, cs);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto t0 = chrono::steady_clock::now();

    int maxAttemptsBase = 5;
    int extraAtt = (int)(3000000LL / total);
    if (extraAtt > 1000) extraAtt = 1000;
    int maxAttempts = max(maxAttemptsBase, extraAtt);

    for (int attempt = 0; attempt < maxAttempts; ++attempt) {
        fill(visited.begin(), visited.end(), 0);
        for (int i = 0; i < total; ++i) degLeft[i] = nbCount[i];

        path.clear();
        int cur = start;
        visited[cur] = 1;
        path.push_back(cur);
        for (int k = 0; k < nbCount[cur]; ++k) {
            int v = nb[cur][k];
            degLeft[v]--;
        }
        int pathLen = 1;

        while (true) {
            if (pathLen == total) break;
            bool lastStep = (pathLen == total - 1);

            Item cand[8];
            int candCnt = 0;

            auto &nblist = nb[cur];
            unsigned char nbdC = nbCount[cur];

            for (int i = 0; i < nbdC; ++i) {
                int v = nblist[i];
                if (visited[v]) continue;
                unsigned char d = degLeft[v];
                if (!lastStep && d == 0) continue;
                cand[candCnt].d = d;
                cand[candCnt].v = v;
                ++candCnt;
            }

            if (candCnt == 0) break;

            sort(cand, cand + candCnt, [](const Item &a, const Item &b) {
                return a.d < b.d;
            });

            int K = 3;
            int use = (candCnt < K ? candCnt : K);
            int chosIdx = (use == 1 ? 0 : (int)(rng() % use));
            int nxt = cand[chosIdx].v;

            cur = nxt;
            visited[cur] = 1;
            path.push_back(cur);
            ++pathLen;

            auto &lst = nb[cur];
            unsigned char lcnt = nbCount[cur];
            for (int i = 0; i < lcnt; ++i) {
                int v = lst[i];
                if (!visited[v]) degLeft[v]--;
            }
        }

        if ((int)path.size() > (int)bestPath.size()) {
            bestPath = path;
            if ((int)bestPath.size() == total) break;
        }

        if (attempt % 10 == 9) {
            auto now = chrono::steady_clock::now();
            long double elapsed =
                chrono::duration_cast<chrono::duration<long double>>(now - t0).count();
            if (elapsed > 0.9L) break;
        }
    }

    int l = (int)bestPath.size();
    cout << l << '\n';
    for (int i = 0; i < l; ++i) {
        int u = bestPath[i];
        int r = u / N;
        int c = u % N;
        cout << (r + 1) << ' ' << (c + 1);
        if (i + 1 < l) cout << '\n';
    }

    return 0;
}