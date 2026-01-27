#include <bits/stdc++.h>
using namespace std;

static inline int manhattan(pair<int,int> a, pair<int,int> b){
    return abs(a.first - b.first) + abs(a.second - b.second);
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if(!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;
    vector<string> grid(N);
    for(int i=0;i<N;i++){
        cin >> grid[i];
    }
    vector<string> words(M);
    for(int k=0;k<M;k++){
        cin >> words[k];
    }

    // Build a superstring containing all words using greedy pairwise merge with overlap up to 5.
    auto overlap = [&](const string& a, const string& b)->int{
        int maxk = min(5, (int)min(a.size(), b.size()));
        for(int k=maxk;k>=1;k--){
            bool ok = true;
            for(int i=0;i<k;i++){
                if(a[a.size()-k+i] != b[i]){ ok=false; break; }
            }
            if(ok) return k;
        }
        return 0;
    };

    vector<string> seq = words;
    while(seq.size() > 1){
        int n = (int)seq.size();
        int bi=-1, bj=-1, bk=-1;
        int bestSum = INT_MAX;
        for(int i=0;i<n;i++){
            for(int j=0;j<n;j++){
                if(i==j) continue;
                int k = overlap(seq[i], seq[j]);
                if(k > bk){
                    bk = k;
                    bi = i; bj = j;
                    bestSum = (int)seq[i].size() + (int)seq[j].size();
                }else if(k == bk){
                    int sum = (int)seq[i].size() + (int)seq[j].size();
                    if(sum < bestSum){
                        bestSum = sum;
                        bi = i; bj = j;
                    }
                }
            }
        }
        if(bi == -1 || bj == -1){
            // Fallback: just concatenate last two
            bi = 0; bj = 1; bk = 0;
        }
        string merged = seq[bi] + seq[bj].substr(bk);
        vector<string> nxt;
        nxt.reserve(n-1);
        for(int i=0;i<n;i++){
            if(i==bi || i==bj) continue;
            nxt.push_back(move(seq[i]));
        }
        nxt.push_back(move(merged));
        seq.swap(nxt);
    }

    string S = seq.empty() ? string() : seq[0];

    // Positions for each letter
    vector<vector<pair<int,int>>> pos(26);
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            char c = grid[i][j];
            pos[c - 'A'].push_back({i,j});
        }
    }

    int L = (int)S.size();
    if(L == 0){
        // Output nothing
        return 0;
    }

    const long long INF = (1LL<<60);
    vector<vector<int>> parent(L);  // parent[t][idx] -> index in positions of S[t-1]
    vector<long long> dp_prev, dp_cur;
    vector<pair<int,int>> pos_prev, pos_cur;
    vector<int> idx_map_prev, idx_map_cur;

    // t = 0
    {
        int c0 = S[0] - 'A';
        int sz0 = (int)pos[c0].size();
        dp_prev.assign(sz0, INF);
        parent[0].assign(sz0, -1);
        for(int j=0;j<sz0;j++){
            dp_prev[j] = manhattan({si,sj}, pos[c0][j]) + 1;
        }
        pos_prev = pos[c0];
    }

    // t >= 1
    for(int t=1;t<L;t++){
        int cprev = S[t-1] - 'A';
        int ccur  = S[t] - 'A';
        int m = (int)pos_prev.size();
        int n = (int)pos[ccur].size();
        dp_cur.assign(n, INF);
        parent[t].assign(n, -1);
        for(int j=0;j<n;j++){
            long long best = INF;
            int best_i = -1;
            for(int i=0;i<m;i++){
                long long cand = dp_prev[i] + manhattan(pos_prev[i], pos[ccur][j]) + 1;
                if(cand < best){
                    best = cand;
                    best_i = i;
                }
            }
            dp_cur[j] = best;
            parent[t][j] = best_i;
        }
        dp_prev.swap(dp_cur);
        pos_prev = pos[ccur];
    }

    // Reconstruct best path
    int last_letter = S[L-1] - 'A';
    int last_sz = (int)pos[last_letter].size();
    long long best_cost = INF;
    int best_idx = -1;
    for(int j=0;j<last_sz;j++){
        if(dp_prev[j] < best_cost){
            best_cost = dp_prev[j];
            best_idx = j;
        }
    }

    vector<pair<int,int>> path(L);
    int cur_idx = best_idx;
    for(int t=L-1;t>=0;t--){
        int c = S[t] - 'A';
        path[t] = pos[c][cur_idx];
        if(t>0){
            cur_idx = parent[t][cur_idx];
        }
    }

    // Output sequence of coordinates
    for(int t=0;t<L;t++){
        cout << path[t].first << " " << path[t].second << "\n";
    }

    return 0;
}