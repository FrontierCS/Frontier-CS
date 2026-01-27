#include <bits/stdc++.h>
using namespace std;

using pii = pair<int,int>;
using ll = long long;

static bool isPrime(int x){
    if(x<2) return false;
    if(x%2==0) return x==2;
    for(int d=3; (ll)d*d<=x; d+=2) if(x%d==0) return false;
    return true;
}
static int nextPrime(int x){
    if(x<=2) return 2;
    if(x%2==0) x++;
    while(!isPrime(x)) x+=2;
    return x;
}

static int ceil_sqrt_ll(long long v){
    long long r = sqrt((long double)v);
    while(r*r < v) ++r;
    while((r-1)*(r-1) >= v) --r;
    return (int)r;
}

struct Solution {
    int n, m;
    vector<pii> ans;

    // mode 0: rows as lines over columns points (mod p)
    // mode 1: columns as lines over rows points (mod q)
    vector<pii> construct_rows_as_lines(int n, int m){
        vector<pii> res;
        if(n==0 || m==0) return res;
        int p = nextPrime(ceil_sqrt_ll(m));
        int L = p*p + p;

        // map columns j -> point (x,y) in F_p^2 using lex order x = j / p, y = j % p
        vector<int> X(m), Y(m);
        for(int j=0;j<m;++j){
            X[j] = j / p;
            Y[j] = j % p;
        }

        vector<int> cnt(L,0);
        // For each point, increment all lines it lies on
        for(int j=0;j<m;++j){
            int x = X[j], y = Y[j];
            // non-vertical lines y = a x + b (mod p)
            // for each a, b = y - a x mod p
            for(int a=0;a<p;++a){
                int b = ( (y - (int)((1LL*a*x)%p)) % p + p ) % p;
                int id = a*p + b;
                cnt[id]++;
            }
            // vertical line x = c
            int idv = p*p + x;
            cnt[idv]++;
        }

        // pick top min(n, lines with positive count) lines
        vector<int> ids(L);
        iota(ids.begin(), ids.end(), 0);
        sort(ids.begin(), ids.end(), [&](int a, int b){
            if(cnt[a]!=cnt[b]) return cnt[a] > cnt[b];
            return a < b;
        });

        int take = 0;
        vector<int> chosen;
        for(int idx : ids){
            if(cnt[idx]==0) break;
            chosen.push_back(idx);
            if((int)chosen.size() == n) break;
        }
        take = (int)chosen.size();

        // generate pairs
        res.reserve( (ll)take * ( (m + p - 1) / p ) + 1 );
        for(int i=0;i<take;++i){
            int id = chosen[i];
            int r = i + 1;
            if(id < p*p){
                int a = id / p;
                int b = id % p;
                for(int j=0;j<m;++j){
                    int x = X[j], y = Y[j];
                    if( ((int)(( (1LL*a*x + b) % p + p) % p)) == y ){
                        res.emplace_back(r, j+1);
                    }
                }
            }else{
                int c = id - p*p;
                for(int j=0;j<m;++j){
                    if(X[j]==c){
                        res.emplace_back(r, j+1);
                    }
                }
            }
        }
        // If n > take, remaining rows empty (no pairs)
        return res;
    }

    vector<pii> construct_cols_as_lines(int n, int m){
        vector<pii> res;
        if(n==0 || m==0) return res;
        int q = nextPrime(ceil_sqrt_ll(n));
        int L = q*q + q;

        // map rows i -> point (x,y) with i from 0..n-1
        vector<int> X(n), Y(n);
        for(int i=0;i<n;++i){
            X[i] = i / q;
            Y[i] = i % q;
        }

        vector<int> cnt(L,0);
        // For each point (row), increment all lines it lies on
        for(int i=0;i<n;++i){
            int x = X[i], y = Y[i];
            for(int a=0;a<q;++a){
                int b = ( (y - (int)((1LL*a*x)%q)) % q + q ) % q;
                int id = a*q + b;
                cnt[id]++;
            }
            int idv = q*q + x;
            cnt[idv]++;
        }

        vector<int> ids(L);
        iota(ids.begin(), ids.end(), 0);
        sort(ids.begin(), ids.end(), [&](int a, int b){
            if(cnt[a]!=cnt[b]) return cnt[a] > cnt[b];
            return a < b;
        });

        int take = 0;
        vector<int> chosen;
        for(int idx : ids){
            if(cnt[idx]==0) break;
            chosen.push_back(idx);
            if((int)chosen.size() == m) break;
        }
        take = (int)chosen.size();

        // For each selected line -> assign to a column
        res.reserve( (ll)take * ( (n + q - 1) / q ) + 1 );
        for(int j=0;j<take;++j){
            int id = chosen[j];
            int c = j + 1; // column index
            if(id < q*q){
                int a = id / q;
                int b = id % q;
                for(int i=0;i<n;++i){
                    int x = X[i], y = Y[i];
                    if( ((int)(( (1LL*a*x + b) % q + q) % q)) == y ){
                        res.emplace_back(i+1, c);
                    }
                }
            }else{
                int cx = id - q*q;
                for(int i=0;i<n;++i){
                    if(X[i]==cx){
                        res.emplace_back(i+1, c);
                    }
                }
            }
        }
        return res;
    }

    void solve(){
        ios::sync_with_stdio(false);
        cin.tie(nullptr);
        cin >> n >> m;

        if(n==1 || m==1){
            vector<pii> all;
            all.reserve((size_t)n*(size_t)m);
            for(int i=1;i<=n;++i){
                for(int j=1;j<=m;++j){
                    all.emplace_back(i,j);
                }
            }
            cout << all.size() << "\n";
            for(auto &pr: all){
                cout << pr.first << " " << pr.second << "\n";
            }
            return;
        }

        // Build both constructions and choose better
        vector<pii> A = construct_rows_as_lines(n,m);
        vector<pii> B = construct_cols_as_lines(n,m);

        if(B.size() > A.size()){
            cout << B.size() << "\n";
            for(auto &pr: B){
                cout << pr.first << " " << pr.second << "\n";
            }
        }else{
            cout << A.size() << "\n";
            for(auto &pr: A){
                cout << pr.first << " " << pr.second << "\n";
            }
        }
    }
};

int main(){
    Solution s;
    s.solve();
    return 0;
}