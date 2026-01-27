#include <bits/stdc++.h>
using namespace std;

static bool is_prime(int x){
    if(x < 2) return false;
    if(x % 2 == 0) return x == 2;
    for(int d = 3; 1LL*d*d <= x; d += 2){
        if(x % d == 0) return false;
    }
    return true;
}

static int next_prime_at_least(int x){
    if(x < 2) x = 2;
    while(!is_prime(x)) ++x;
    return x;
}

static int ceil_sqrt(long long x){
    long long r = sqrtl((long double)x);
    while(r*r < x) ++r;
    while((r-1)*(r-1) >= x) --r;
    return (int)r;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if(!(cin >> n >> m)) return 0;

    vector<pair<int,int>> ans;

    if(n <= m){
        // Row-based construction
        int LB = ceil_sqrt(n);
        int t = max(LB, 2);
        int p = next_prime_at_least(t);

        vector<vector<int>> col(p, vector<int>(p, -1));
        for(int c = 0; c < m; ++c){
            int x = c % p;
            int y = (c / p) % p;
            if(col[x][y] == -1) col[x][y] = c;
        }

        for(int r = 0; r < n; ++r){
            int a = r % p;
            int b = (r / p) % p;
            for(int x = 0; x < p; ++x){
                int y = ( (long long)a * x + b ) % p;
                int c = col[x][y];
                if(c != -1){
                    ans.emplace_back(r+1, c+1);
                }
            }
        }
    }else{
        // Column-based construction
        int LB = ceil_sqrt(m);
        int t = max((int)floor(sqrt((long double)n)), LB);
        t = max(t, 2);
        int q = next_prime_at_least(t);

        vector<vector<int>> rowxy(q, vector<int>(q, -1));
        for(int r = 0; r < n; ++r){
            int x = r % q;
            int y = (r / q) % q;
            if(rowxy[x][y] == -1) rowxy[x][y] = r;
        }

        for(int j = 0; j < m; ++j){
            int a = j % q;
            int b = (j / q) % q;
            for(int x = 0; x < q; ++x){
                int y = ( (long long)a * x + b ) % q;
                int r = rowxy[x][y];
                if(r != -1){
                    ans.emplace_back(r+1, j+1);
                }
            }
        }
    }

    cout << ans.size() << "\n";
    for(auto &pr : ans){
        cout << pr.first << " " << pr.second << "\n";
    }
    return 0;
}