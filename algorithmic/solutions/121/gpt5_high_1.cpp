#include <bits/stdc++.h>
using namespace std;

struct Pattern {
    vector<int> pos;
    vector<unsigned char> val;
    string s; // keep for quick access during dominance/conflict checks
};

static inline int lcode(char c){
    if(c=='A') return 0;
    if(c=='C') return 1;
    if(c=='G') return 2;
    if(c=='T') return 3;
    return -1;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if(!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for(int i=0;i<m;i++) cin >> s[i];

    // Build pos lists
    vector<Pattern> pats0(m);
    for(int i=0;i<m;i++){
        pats0[i].s = s[i];
        for(int j=0;j<n;j++){
            int c = lcode(s[i][j]);
            if(c!=-1){
                pats0[i].pos.push_back(j);
                pats0[i].val.push_back((unsigned char)c);
            }
        }
    }

    // Remove dominated patterns: if E[i] subset of E[j] then remove i
    vector<char> removed(m, 0);
    for(int i=0;i<m;i++){
        if(removed[i]) continue;
        for(int j=0;j<m;j++){
            if(i==j || removed[j]) continue;
            // Check if E[i] ⊆ E[j]
            bool subset = true;
            for(size_t k=0;k<pats0[i].pos.size();k++){
                int p = pats0[i].pos[k];
                char cj = s[j][p];
                if(cj!='?' && lcode(cj) != (int)pats0[i].val[k]){
                    subset = false; break;
                }
            }
            if(subset){
                removed[i] = 1;
                break;
            }
        }
    }
    vector<Pattern> pats;
    pats.reserve(m);
    for(int i=0;i<m;i++){
        if(!removed[i]) pats.push_back(pats0[i]);
    }
    m = (int)pats.size();

    // If no patterns (shouldn't happen), probability 0
    if(m==0){
        cout.setf(std::ios::fixed); cout<<setprecision(12)<<0.0<<"\n";
        return 0;
    }

    // Sort patterns by number of fixed positions (descending) to improve pruning
    vector<int> ord(m);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b){
        if(pats[a].pos.size() != pats[b].pos.size())
            return pats[a].pos.size() > pats[b].pos.size();
        return a < b;
    });

    vector<Pattern> p2(m);
    for(int i=0;i<m;i++){
        p2[i] = pats[ord[i]];
    }
    pats.swap(p2);

    // Rebuild conflicts mask after sorting
    vector<unsigned long long> confMask(m, 0ULL);
    for(int i=0;i<m;i++){
        for(int j=i+1;j<m;j++){
            // check conflict between pats[i], pats[j]
            bool conflict = false;
            // iterate smaller pos list
            if(pats[i].pos.size() > pats[j].pos.size()){
                // swap roles
                for(size_t k=0;k<pats[j].pos.size();k++){
                    int p = pats[j].pos[k];
                    char ci = pats[i].s[p];
                    if(ci!='?' && lcode(ci) != (int)pats[j].val[k]){
                        conflict = true; break;
                    }
                }
            }else{
                for(size_t k=0;k<pats[i].pos.size();k++){
                    int p = pats[i].pos[k];
                    char cj = pats[j].s[p];
                    if(cj!='?' && lcode(cj) != (int)pats[i].val[k]){
                        conflict = true; break;
                    }
                }
            }
            if(conflict){
                confMask[i] |= (1ULL<<j);
                confMask[j] |= (1ULL<<i);
            }
        }
    }

    // Precompute pow(1/4, k)
    vector<long double> pow4(n+1);
    pow4[0] = 1.0L;
    for(int i=1;i<=n;i++) pow4[i] = pow4[i-1] * 0.25L;

    // Assign array and stack for changes
    vector<signed char> assign(n, -1);
    vector<int> chstack; chstack.reserve(n);
    int assigned_cnt = 0;

    long double ans = 0.0L;

    function<void(int, bool, bool, unsigned long long)> dfs = [&](int idx, bool nonempty, bool odd, unsigned long long chosenMask){
        if(idx == m){
            if(nonempty){
                ans += (odd ? 1.0L : -1.0L) * pow4[assigned_cnt];
            }
            return;
        }
        // Exclude current
        dfs(idx+1, nonempty, odd, chosenMask);

        // Include current - early pairwise conflict prune
        if((confMask[idx] & chosenMask) != 0ULL){
            return;
        }
        size_t oldsz = chstack.size();
        int addc = 0;
        bool conflict = false;
        // Apply constraints
        auto &P = pats[idx];
        for(size_t k=0;k<P.pos.size();k++){
            int p = P.pos[k];
            int v = (int)P.val[k];
            signed char cur = assign[p];
            if(cur == -1){
                assign[p] = (signed char)v;
                chstack.push_back(p);
                addc++;
            }else if(cur != v){
                conflict = true;
                break;
            }
        }
        if(!conflict){
            assigned_cnt += addc;
            dfs(idx+1, true, !odd, chosenMask | (1ULL<<idx));
            assigned_cnt -= addc;
        }
        // Revert
        while(chstack.size() > oldsz){
            int p = chstack.back(); chstack.pop_back();
            assign[p] = -1;
        }
    };

    dfs(0, false, false, 0ULL);

    cout.setf(std::ios::fixed);
    cout << setprecision(12) << (double)ans << "\n";
    return 0;
}