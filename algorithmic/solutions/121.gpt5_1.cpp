#include <bits/stdc++.h>
using namespace std;

struct Pattern {
    vector<uint64_t> letter[4]; // positions where this pattern has A/C/G/T
    vector<uint64_t> uni;       // union of letters (any fixed position)
    int cntFixed = 0;
};

static inline int lidx(char c){
    if(c=='A') return 0;
    if(c=='C') return 1;
    if(c=='G') return 2;
    if(c=='T') return 3;
    return -1;
}

int n, m;
vector<string> s;

// Check if a generalizes b: for all j, a[j]=='?' or a[j]==b[j]
bool generalizes(const string& a, const string& b){
    for(int i=0;i<(int)a.size();++i){
        if(a[i]!='?' && a[i]!=b[i]) return false;
    }
    return true;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin>>n>>m;
    s.resize(m);
    for(int i=0;i<m;++i) cin>>s[i];

    // Remove duplicates
    vector<string> t;
    t.reserve(m);
    {
        unordered_set<string> seen;
        seen.reserve(m*2+1);
        for(int i=0;i<m;++i){
            if(seen.insert(s[i]).second) t.push_back(s[i]);
        }
    }
    s.swap(t);
    m = (int)s.size();

    // If any is all '?', probability is 1
    for(int i=0;i<m;++i){
        bool allq = true;
        for(char c: s[i]) if(c!='?'){ allq=false; break; }
        if(allq){
            cout.setf(std::ios::fixed); cout<<setprecision(12)<<1.0<<"\n";
            return 0;
        }
    }

    // Remove dominated strings: if exists j != i with s[j] generalizes s[i], remove i
    vector<bool> del(m,false);
    for(int i=0;i<m;++i){
        if(del[i]) continue;
        for(int j=0;j<m;++j){
            if(i==j || del[i]) continue;
            if(generalizes(s[j], s[i])){
                del[i]=true;
            }
        }
    }
    vector<string> u;
    for(int i=0;i<m;++i) if(!del[i]) u.push_back(s[i]);
    s.swap(u);
    m = (int)s.size();

    if(m==0){
        cout.setf(std::ios::fixed); cout<<setprecision(12)<<0.0<<"\n";
        return 0;
    }

    // Build Patterns with bitsets over positions
    int W = (n + 63) / 64;
    vector<Pattern> P(m);
    for(int i=0;i<m;++i){
        P[i].uni.assign(W, 0);
        for(int l=0;l<4;++l) P[i].letter[l].assign(W, 0);
        int cnt = 0;
        for(int j=0;j<n;++j){
            char c = s[i][j];
            int id = lidx(c);
            if(id!=-1){
                int w = j>>6, b = j&63;
                P[i].letter[id][w] |= (uint64_t(1) << b);
                P[i].uni[w] |= (uint64_t(1) << b);
                cnt++;
            }
        }
        P[i].cntFixed = cnt;
    }

    // Sort by decreasing number of fixed letters to increase pruning
    vector<int> order(m);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if(P[a].cntFixed != P[b].cntFixed) return P[a].cntFixed > P[b].cntFixed;
        return a < b;
    });
    vector<Pattern> Q(m);
    for(int k=0;k<m;++k) Q[k] = P[order[k]];
    P.swap(Q);

    // Prepare recursion helpers
    vector<uint64_t> assign[4];
    for(int l=0;l<4;++l) assign[l].assign(W, 0);
    vector<uint64_t> unionAll(W, 0);

    // Pre-allocate storage for added bits at each recursion depth to avoid allocations
    vector<vector<uint64_t>> addedA(m, vector<uint64_t>(W,0));
    vector<vector<uint64_t>> addedC(m, vector<uint64_t>(W,0));
    vector<vector<uint64_t>> addedG(m, vector<uint64_t>(W,0));
    vector<vector<uint64_t>> addedT(m, vector<uint64_t>(W,0));
    vector<vector<uint64_t>> addedUni(m, vector<uint64_t>(W,0));

    // Precompute pow(1/4, k)
    vector<long double> powinv4(n+1);
    powinv4[0] = 1.0L;
    for(int i=1;i<=n;++i) powinv4[i] = powinv4[i-1] * 0.25L;

    long double ans = 0.0L;

    function<void(int,int,int)> dfs = [&](int idx, int includedCount, int forcedCount){
        if(idx == m){
            return;
        }
        // Exclude current index
        dfs(idx+1, includedCount, forcedCount);

        // Include current index if no conflict
        bool conflict = false;
        // Check conflicts
        for(int w=0; w<W && !conflict; ++w){
            uint64_t uAll = unionAll[w];
            // For each letter l: conflict if (P[idx].letter[l] & (unionAll ^ assign[l])) != 0
            uint64_t x;
            // A
            x = P[idx].letter[0][w] & (uAll ^ assign[0][w]);
            if(x){ conflict = true; break; }
            // C
            x = P[idx].letter[1][w] & (uAll ^ assign[1][w]);
            if(x){ conflict = true; break; }
            // G
            x = P[idx].letter[2][w] & (uAll ^ assign[2][w]);
            if(x){ conflict = true; break; }
            // T
            x = P[idx].letter[3][w] & (uAll ^ assign[3][w]);
            if(x){ conflict = true; break; }
        }
        if(conflict) return;

        // Compute added bits and update
        int depth = idx;
        int delta = 0;
        for(int w=0; w<W; ++w){
            uint64_t uAll = unionAll[w];

            uint64_t addA = P[idx].letter[0][w] & ~assign[0][w];
            uint64_t addC = P[idx].letter[1][w] & ~assign[1][w];
            uint64_t addG = P[idx].letter[2][w] & ~assign[2][w];
            uint64_t addT = P[idx].letter[3][w] & ~assign[3][w];

            addedA[depth][w] = addA;
            addedC[depth][w] = addC;
            addedG[depth][w] = addG;
            addedT[depth][w] = addT;

            uint64_t addU = P[idx].uni[w] & ~uAll;
            addedUni[depth][w] = addU;
            delta += __builtin_popcountll(addU);

            assign[0][w] |= P[idx].letter[0][w];
            assign[1][w] |= P[idx].letter[1][w];
            assign[2][w] |= P[idx].letter[2][w];
            assign[3][w] |= P[idx].letter[3][w];
            unionAll[w] |= P[idx].uni[w];
        }

        int newForced = forcedCount + delta;
        int newIncluded = includedCount + 1;
        long double add = powinv4[newForced] * ((newIncluded & 1) ? 1.0L : -1.0L);
        ans += add;

        dfs(idx+1, newIncluded, newForced);

        // revert
        for(int w=0; w<W; ++w){
            assign[0][w] ^= addedA[depth][w];
            assign[1][w] ^= addedC[depth][w];
            assign[2][w] ^= addedG[depth][w];
            assign[3][w] ^= addedT[depth][w];
            unionAll[w] ^= addedUni[depth][w];
        }
    };

    dfs(0, 0, 0);

    cout.setf(std::ios::fixed);
    cout<<setprecision(15)<<(double)ans<<"\n";
    return 0;
}