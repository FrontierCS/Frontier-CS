#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;
    vector<string> A(n), B(n);
    for (int i = 0; i < n; ++i) cin >> A[i];
    // There may be blank lines; operator>> skips them, so just read next n strings
    for (int i = 0; i < n; ++i) cin >> B[i];

    struct Preset { int r, c; vector<string> s; };
    vector<Preset> pres(k);
    for (int t = 0; t < k; ++t) {
        int r, c;
        cin >> r >> c;
        pres[t].r = r; pres[t].c = c;
        pres[t].s.resize(r);
        for (int i = 0; i < r; ++i) cin >> pres[t].s[i];
    }

    auto idx64 = [&](char ch)->int{
        if ('a'<=ch && ch<='z') return ch-'a';
        if ('A'<=ch && ch<='Z') return 26 + (ch-'A');
        if ('0'<=ch && ch<='9') return 52 + (ch-'0');
        return -1;
    };

    const int SZ = 62;
    array<int,SZ> ca{}, cb{};
    ca.fill(0); cb.fill(0);
    for (int i=0;i<n;i++) for (int j=0;j<m;j++){ ca[idx64(A[i][j])]++; cb[idx64(B[i][j])]++; }

    vector<tuple<int,int,int>> ops; // (op,x,y)

    auto do_swap = [&](pair<int,int> p1, pair<int,int> p2){
        int x1=p1.first, y1=p1.second, x2=p2.first, y2=p2.second;
        if (x1==x2) {
            int x=x1, y=min(y1,y2);
            ops.emplace_back(-1, x+1, y+1);
        } else {
            int x=min(x1,x2), y=y1;
            ops.emplace_back(-4, x+1, y+1);
        }
        swap(A[x1][y1], A[x2][y2]);
    };

    bool solved = false;

    if (ca == cb) {
        // Snake order mapping
        vector<pair<int,int>> path;
        path.reserve(n*m);
        for (int i=0;i<n;i++){
            if (i%2==0){
                for (int j=0;j<m;j++) path.emplace_back(i,j);
            } else {
                for (int j=m-1;j>=0;j--) path.emplace_back(i,j);
            }
        }
        string seq, tgt;
        seq.reserve(n*m); tgt.reserve(n*m);
        for (auto [x,y]: path) seq.push_back(A[x][y]);
        for (auto [x,y]: path) tgt.push_back(B[x][y]);

        int N = n*m;
        for (int t=0;t<N;t++){
            if (seq[t]==tgt[t]) continue;
            int p=t+1;
            while (p<N && seq[p]!=tgt[t]) ++p;
            if (p==N) { /*shouldn't happen*/ break; }
            for (int q=p; q>t; --q){
                // swap positions q-1 and q along path
                do_swap(path[q-1], path[q]);
                swap(seq[q-1], seq[q]);
            }
        }
        solved = true;
    } else {
        // Try greedy preset cover to paint target
        struct Rect { int op; int x; int y; int r; int c; int gain; };
        vector<Rect> rects;
        for (int p=0;p<k;p++){
            int r = pres[p].r, c = pres[p].c;
            for (int i=0;i+r<=n;i++){
                for (int j=0;j+c<=m;j++){
                    bool ok=true;
                    for (int x=0;x<r && ok;x++){
                        for (int y=0;y<c;y++){
                            if (pres[p].s[x][y]!=B[i+x][j+y]) { ok=false; break; }
                        }
                    }
                    if (ok) {
                        rects.push_back({p, i, j, r, c, 0});
                    }
                }
            }
        }
        if (!rects.empty()){
            vector<vector<char>> covered(n, vector<char>(m, 0));
            vector<int> chosen;
            int coveredCount = 0;
            for (int iter=0; iter<100000 && coveredCount < n*m; ++iter){
                int best = -1, bestGain = 0;
                for (int idx=0; idx<(int)rects.size(); ++idx){
                    int gain = 0;
                    auto &rc = rects[idx];
                    for (int x=0;x<rc.r;x++){
                        for (int y=0;y<rc.c;y++){
                            if (!covered[rc.x+x][rc.y+y]) gain++;
                        }
                    }
                    rects[idx].gain = gain;
                    if (gain > bestGain){
                        bestGain = gain;
                        best = idx;
                    }
                }
                if (bestGain == 0) break;
                auto rc = rects[best];
                chosen.push_back(best);
                for (int x=0;x<rc.r;x++){
                    for (int y=0;y<rc.c;y++){
                        if (!covered[rc.x+x][rc.y+y]){
                            covered[rc.x+x][rc.y+y] = 1;
                            coveredCount++;
                        }
                    }
                }
                if ((int)chosen.size() > 400) break;
            }
            if (coveredCount == n*m && (int)chosen.size() <= 400){
                for (int id: chosen){
                    auto &rc = rects[id];
                    ops.emplace_back(rc.op+1, rc.x+1, rc.y+1);
                }
                solved = true;
            }
        }
    }

    if (!solved) {
        cout << -1 << '\n';
        return 0;
    }

    cout << ops.size() << '\n';
    for (auto &t : ops){
        int op,x,y;
        tie(op,x,y) = t;
        cout << op << ' ' << x << ' ' << y << '\n';
    }
    return 0;
}