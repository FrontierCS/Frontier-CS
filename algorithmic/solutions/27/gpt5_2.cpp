#include <bits/stdc++.h>
using namespace std;

struct Line {
    bool vertical; // false: y = s*x + b, true: x = s
    int s; // slope or x for vertical
    int b; // intercept (unused for vertical)
};

static inline int isPrime(int x){
    if(x < 2) return 0;
    for(int d=2; 1LL*d*d<=x; ++d) if(x%d==0) return 0;
    return 1;
}
static inline int nextPrime(int x){
    if(x <= 2) return 2;
    int v = x;
    while(!isPrime(v)) ++v;
    return v;
}

vector<pair<int,int>> build_star(int n, int m){
    vector<pair<int,int>> ans;
    ans.reserve(n + max(0, m-1));
    // Fill first column with all rows
    for(int r=1; r<=n; ++r) ans.emplace_back(r, 1);
    // For each other column, put one point
    for(int c=2; c<=m; ++c){
        int r = (c-2) % n + 1;
        ans.emplace_back(r, c);
    }
    return ans;
}

vector<pair<int,int>> build_AG(int n, int m){
    int q = nextPrime(max(2, (int)ceil(sqrt((double)max(n, m)))));
    int q2 = q*q;
    int totalLines = q2 + q;

    vector<Line> lines;
    lines.reserve(totalLines);
    for(int s=0; s<q; ++s){
        for(int b=0; b<q; ++b){
            lines.push_back({false, s, b});
        }
    }
    for(int v=0; v<q; ++v){
        lines.push_back({true, v, 0});
    }

    vector<char> selectedP(q2, 0);
    for(int i=0; i<n; ++i) selectedP[i] = 1;

    vector<int> selectedLineIdx;
    vector<int> pidx(q2);
    iota(pidx.begin(), pidx.end(), 0);

    int iterations = 2;
    for(int it=0; it<iterations; ++it){
        // Compute scores for all lines relative to selectedP
        vector<int> lineScore(lines.size(), 0);
        for(size_t i=0; i<lines.size(); ++i){
            const Line &L = lines[i];
            int cnt = 0;
            if(!L.vertical){
                int y = L.b;
                for(int x=0; x<q; ++x){
                    int id = x*q + y;
                    if(selectedP[id]) ++cnt;
                    y += L.s;
                    if(y >= q) y -= q;
                }
            }else{
                int base = L.s * q;
                for(int y=0; y<q; ++y){
                    int id = base + y;
                    if(selectedP[id]) ++cnt;
                }
            }
            lineScore[i] = cnt;
        }
        vector<int> idx(lines.size());
        iota(idx.begin(), idx.end(), 0);
        sort(idx.begin(), idx.end(), [&](int a, int b){
            if(lineScore[a] != lineScore[b]) return lineScore[a] > lineScore[b];
            return a < b;
        });
        int takeM = min((int)idx.size(), m);
        selectedLineIdx.assign(idx.begin(), idx.begin() + takeM);

        // Compute point scores for selected lines
        vector<int> pscore(q2, 0);
        for(int li = 0; li < takeM; ++li){
            const Line &L = lines[selectedLineIdx[li]];
            if(!L.vertical){
                int y = L.b;
                for(int x=0; x<q; ++x){
                    int id = x*q + y;
                    ++pscore[id];
                    y += L.s;
                    if(y >= q) y -= q;
                }
            }else{
                int base = L.s * q;
                for(int y=0; y<q; ++y){
                    int id = base + y;
                    ++pscore[id];
                }
            }
        }

        // Select top n points by pscore
        iota(pidx.begin(), pidx.end(), 0);
        sort(pidx.begin(), pidx.end(), [&](int a, int b){
            if(pscore[a] != pscore[b]) return pscore[a] > pscore[b];
            return a < b;
        });
        fill(selectedP.begin(), selectedP.end(), 0);
        for(int i=0; i<n; ++i) selectedP[pidx[i]] = 1;
    }

    // Final mapping of point -> row id
    vector<int> rowOfPoint(q2, -1);
    for(int i=0; i<n; ++i){
        rowOfPoint[pidx[i]] = i+1;
    }

    // Build final answer
    vector<pair<int,int>> ans;
    ans.reserve((size_t)n * min(m, q)); // rough
    int takeM = min((int)selectedLineIdx.size(), m);
    for(int ci=0; ci<takeM; ++ci){
        int col = ci + 1;
        const Line &L = lines[selectedLineIdx[ci]];
        if(!L.vertical){
            int y = L.b;
            for(int x=0; x<q; ++x){
                int id = x*q + y;
                int r = rowOfPoint[id];
                if(r != -1) ans.emplace_back(r, col);
                y += L.s;
                if(y >= q) y -= q;
            }
        }else{
            int base = L.s * q;
            for(int y=0; y<q; ++y){
                int id = base + y;
                int r = rowOfPoint[id];
                if(r != -1) ans.emplace_back(r, col);
            }
        }
    }
    return ans;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if(!(cin >> n >> m)) return 0;

    // Special trivial cases to ensure high score and correctness
    if(n == 1 || m == 1){
        vector<pair<int,int>> ans;
        ans.reserve((size_t)n * m);
        for(int r=1; r<=n; ++r)
            for(int c=1; c<=m; ++c)
                ans.emplace_back(r,c);
        cout << ans.size() << "\n";
        for(auto &p: ans) cout << p.first << " " << p.second << "\n";
        return 0;
    }

    // Candidate 1: Star construction
    auto ansStar = build_star(n, m);

    // Candidate 2: Affine plane based
    auto ansAG = build_AG(n, m);

    // Pick the better one
    const auto &best = (ansAG.size() >= ansStar.size() ? ansAG : ansStar);

    cout << best.size() << "\n";
    for(auto &p : best){
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}