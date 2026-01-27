#include <bits/stdc++.h>
using namespace std;

static string varName(int i){ return string(1, char('a'+i)); }

static string combine(const vector<string>& parts, char op){
    if(parts.empty()) return "";
    vector<string> cur = parts, nxt;
    while(cur.size() > 1){
        nxt.clear();
        for(size_t i=0;i+1<cur.size();i+=2){
            string s = "(" + cur[i] + op + cur[i+1] + ")";
            nxt.push_back(move(s));
        }
        if(cur.size() & 1) nxt.push_back(cur.back());
        cur.swap(nxt);
    }
    return cur[0];
}

static string build_and(const vector<int>& vars){
    if(vars.empty()) return "T";
    if(vars.size()==1) return varName(vars[0]);
    vector<string> parts;
    parts.reserve(vars.size());
    for(int v: vars) parts.push_back(varName(v));
    return combine(parts, '&');
}

static string build_or(const vector<int>& vars){
    if(vars.empty()) return "F";
    if(vars.size()==1) return varName(vars[0]);
    vector<string> parts;
    parts.reserve(vars.size());
    for(int v: vars) parts.push_back(varName(v));
    return combine(parts, '|');
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin>>T)) return 0;
    while(T--){
        int n; string s;
        cin>>n>>s;
        int N = 1<<n;
        // Check length
        if((int)s.size()!=N){
            cout<<"No\n";
            continue;
        }
        // Monotonicity check
        bool ok = true;
        for(int m=0;m<N && ok;m++){
            if(s[m]=='1'){
                // nothing to check for supersets? still need check that no subset 1 then superset 0 -> we only need to ensure nondecreasing along covering relations
            }
            for(int i=0;i<n;i++){
                if(((m>>i)&1)==0){
                    int m2 = m | (1<<i);
                    if(s[m]>'s'[0]){} // no-op
                    if(s[m]=='1' && s[m2]=='0'){ ok=false; break; }
                }
            }
        }
        if(!ok){
            cout<<"No\n";
            continue;
        }
        // All zero or all one
        bool all0 = true, all1 = true;
        for(char c: s){ if(c=='1') all0=false; else all1=false; }
        cout<<"Yes\n";
        if(all1){ cout<<"T\n"; continue; }
        if(all0){ cout<<"F\n"; continue; }

        // Collect minimal true vectors and maximal false vectors
        vector<vector<int>> minTrue; minTrue.reserve(N);
        vector<vector<int>> maxFalse; maxFalse.reserve(N);

        for(int m=0;m<N;m++){
            if(s[m]=='1'){
                bool minimal = true;
                int x = m;
                while(x){
                    int b = x & -x;
                    int m2 = m ^ b;
                    if(s[m2]=='1'){ minimal=false; break; }
                    x ^= b;
                }
                if(minimal){
                    // variables set to 1
                    vector<int> vars;
                    for(int i=0;i<n;i++) if((m>>i)&1) vars.push_back(i);
                    minTrue.push_back(move(vars));
                }
            }else{
                bool maximal = true;
                for(int i=0;i<n;i++){
                    if(((m>>i)&1)==0){
                        int m2 = m | (1<<i);
                        if(s[m2]=='0'){ maximal=false; break; }
                    }
                }
                if(maximal){
                    // variables which are 0 -> in clause
                    vector<int> vars;
                    for(int i=0;i<n;i++) if(((m>>i)&1)==0) vars.push_back(i);
                    maxFalse.push_back(move(vars));
                }
            }
        }

        // Compute operator counts
        auto count_ops_andlist = [](const vector<vector<int>>& list)->long long{
            if(list.empty()) return 0;
            long long internal = 0;
            for(auto &v: list) if(!v.empty()) internal += (int)v.size() - 1;
            long long top = (long long)list.size() - 1;
            return internal + max(0LL, top);
        };
        long long opsDNF = 0, opsCNF = 0;
        if(!minTrue.empty()){
            long long internal = 0;
            for(auto &v: minTrue) internal += (int)v.size() - 1;
            opsDNF = internal + ((long long)minTrue.size() - 1);
        }else{
            // Shouldn't occur unless all1
            opsDNF = LLONG_MAX/4;
        }
        if(!maxFalse.empty()){
            long long internal = 0;
            for(auto &v: maxFalse) internal += (int)v.size() - 1;
            opsCNF = internal + ((long long)maxFalse.size() - 1);
        }else{
            // Shouldn't occur unless all1
            opsCNF = LLONG_MAX/4;
        }

        // Build smaller
        string expr;
        if(opsDNF <= opsCNF){
            // Build DNF
            if(minTrue.size()==1 && minTrue[0].empty()){
                expr = "T";
            }else{
                vector<string> terms;
                terms.reserve(minTrue.size());
                for(auto &v: minTrue){
                    if(v.empty()) { terms.clear(); terms.push_back("T"); break; }
                    terms.push_back(build_and(v));
                }
                if(terms.size()==1) expr = terms[0];
                else expr = combine(terms, '|');
            }
        }else{
            // Build CNF
            if(maxFalse.size()==1 && maxFalse[0].empty()){
                expr = "F";
            }else{
                vector<string> clauses;
                clauses.reserve(maxFalse.size());
                for(auto &v: maxFalse){
                    if(v.empty()) { clauses.clear(); clauses.push_back("F"); break; }
                    clauses.push_back(build_or(v));
                }
                if(clauses.size()==1) expr = clauses[0];
                else expr = combine(clauses, '&');
            }
        }
        cout<<expr<<"\n";
    }
    return 0;
}