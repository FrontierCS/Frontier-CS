#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> a;

int ask(int x1,int y1,int x2,int y2){
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    int res;
    if(!(cin >> res)) exit(0);
    if(res == -1) exit(0);
    return res;
}

int getVal(int i,int j,bool flipOdd){
    int v = a[i][j];
    if(((i+j)&1) && flipOdd) v ^= 1;
    return v;
}

bool checkPathPalOddDistBruteforce(int x1,int y1,int x2,int y2,bool flipOdd){
    // brute force enumerate all monotone paths from (x1,y1) to (x2,y2)
    // only used for n == 3 (small)
    vector<pair<int,int>> path;
    bool ok = false;
    function<void(int,int)> dfs = [&](int x,int y){
        path.emplace_back(x,y);
        if(x==x2 && y==y2){
            vector<int> vals;
            for(auto &p:path) vals.push_back(getVal(p.first,p.second,flipOdd));
            bool pal = true;
            int L = (int)vals.size();
            for(int i=0;i<L;i++){
                if(vals[i] != vals[L-1-i]){ pal = false; break; }
            }
            if(pal) ok = true;
            path.pop_back();
            return;
        }
        if(x > x2 || y > y2){ path.pop_back(); return; }
        if(!ok){
            if(x+1 <= x2) dfs(x+1,y);
        }
        if(!ok){
            if(y+1 <= y2) dfs(x,y+1);
        }
        path.pop_back();
    };
    dfs(x1,y1);
    return ok;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if(!(cin >> n)) return 0;
    a.assign(n+1, vector<int>(n+1, -1));
    a[1][1] = 1;
    a[n][n] = 0;

    // Fill even parity cells
    for(int s=2; s<=2*n; ++s){
        for(int i=1;i<=n;i++){
            int j = s - i;
            if(j < 1 || j > n) continue;
            if(((i+j)&1) != 0) continue; // even parity only
            if(a[i][j] != -1) continue;
            // try predecessors at distance 2 in allowed direction
            if(i-2 >= 1 && a[i-2][j] != -1){
                int res = ask(i-2,j,i,j);
                a[i][j] = a[i-2][j] ^ (res?0:1);
            } else if(j-2 >= 1 && a[i][j-2] != -1){
                int res = ask(i,j-2,i,j);
                a[i][j] = a[i][j-2] ^ (res?0:1);
            } else if(i-1 >= 1 && j-1 >= 1 && a[i-1][j-1] != -1){
                int res = ask(i-1,j-1,i,j);
                a[i][j] = a[i-1][j-1] ^ (res?0:1);
            }
        }
    }

    // Fill odd parity cells with two seeds
    if(n >= 2){
        a[1][2] = 0;
        a[2][1] = 0;
    }
    for(int s=2; s<=2*n; ++s){
        for(int i=1;i<=n;i++){
            int j = s - i;
            if(j < 1 || j > n) continue;
            if(((i+j)&1) != 1) continue; // odd parity
            if(a[i][j] != -1) continue;
            if(i-2 >= 1 && a[i-2][j] != -1){
                int res = ask(i-2,j,i,j);
                a[i][j] = a[i-2][j] ^ (res?0:1);
            } else if(j-2 >= 1 && a[i][j-2] != -1){
                int res = ask(i,j-2,i,j);
                a[i][j] = a[i][j-2] ^ (res?0:1);
            } else if(i-1 >= 1 && j-1 >= 1 && a[i-1][j-1] != -1){
                int res = ask(i-1,j-1,i,j);
                a[i][j] = a[i-1][j-1] ^ (res?0:1);
            }
        }
    }

    bool flipOdd = false;

    if(n >= 5){
        // Use unique path along row from (1,1) to (1,4)
        int x1=1,y1=1,x2=1,y2=4;
        bool pred = (getVal(x1,y1,false) == getVal(x2,y2,false)) && (getVal(1,2,false) == getVal(1,3,false));
        int ans = ask(x1,y1,x2,y2);
        if(ans != (pred ? 1 : 0)){
            flipOdd = true;
        }
    } else {
        // n == 3 case: search a pair with odd distance (3) where result differs under flip
        bool found = false;
        int sx1=0, sy1=0, sx2=0, sy2=0;
        for(int x1=1; x1<=n && !found; ++x1){
            for(int y1=1; y1<=n && !found; ++y1){
                for(int x2=x1; x2<=n && !found; ++x2){
                    for(int y2=y1; y2<=n && !found; ++y2){
                        int d = (x2 - x1) + (y2 - y1);
                        if(d < 2) continue;
                        if(d % 2 == 0) continue; // need odd length
                        if(x1 + y1 + 2 > x2 + y2) continue;
                        bool f0 = checkPathPalOddDistBruteforce(x1,y1,x2,y2,false);
                        bool f1 = checkPathPalOddDistBruteforce(x1,y1,x2,y2,true);
                        if(f0 != f1){
                            sx1=x1; sy1=y1; sx2=x2; sy2=y2;
                            found = true;
                        }
                    }
                }
            }
        }
        if(found){
            int ans = ask(sx1,sy1,sx2,sy2);
            bool f0 = checkPathPalOddDistBruteforce(sx1,sy1,sx2,sy2,false);
            if(ans != (f0 ? 1 : 0)){
                flipOdd = true;
            }
        } else {
            // Fallback (shouldn't happen), but if so do an arbitrary odd-length query:
            // Choose (1,1) to (2,3)
            int x1=1,y1=1,x2=2,y2=3;
            bool f0 = checkPathPalOddDistBruteforce(x1,y1,x2,y2,false);
            int ans = ask(x1,y1,x2,y2);
            if(ans != (f0 ? 1 : 0)){
                flipOdd = true;
            }
        }
    }

    // Apply flip if needed
    if(flipOdd){
        for(int i=1;i<=n;i++){
            for(int j=1;j<=n;j++){
                if(((i+j)&1) == 1){
                    a[i][j] ^= 1;
                }
            }
        }
    }

    cout << "!" << '\n';
    for(int i=1;i<=n;i++){
        for(int j=1;j<=n;j++){
            cout << a[i][j];
        }
        cout << '\n';
    }
    cout.flush();
    return 0;
}