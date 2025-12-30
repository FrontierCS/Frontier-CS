#include <bits/stdc++.h>
using namespace std;

int id(char c){
    if ('a' <= c && c <= 'z') return c - 'a';
    if ('A' <= c && c <= 'Z') return 26 + (c - 'A');
    return 52 + (c - '0'); // '0'..'9'
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;
    vector<string> cur(n), tgt(n);
    for (int i = 0; i < n; ++i) cin >> cur[i];
    for (int i = 0; i < n; ++i) cin >> tgt[i];
    for (int p = 0; p < k; ++p){
        int np, mp;
        cin >> np >> mp;
        string s;
        for (int i = 0; i < np; ++i) cin >> s; // ignore content
    }
    
    vector<int> cntA(62,0), cntB(62,0);
    for (int i = 0; i < n; ++i){
        for (int j = 0; j < m; ++j){
            cntA[id(cur[i][j])]++;
            cntB[id(tgt[i][j])]++;
        }
    }
    if (cntA != cntB){
        cout << -1 << "\n";
        return 0;
    }
    
    vector<array<int,3>> ops;
    auto addop = [&](int op, int x, int y){
        ops.push_back({op, x, y});
    };
    
    for (int i = 0; i < n; ++i){
        for (int j = 0; j < m; ++j){
            char need = tgt[i][j];
            if (cur[i][j] == need) continue;
            int bestx = -1, besty = -1, bestd = INT_MAX;
            // Search in row i, columns j..m-1
            for (int y = j; y < m; ++y){
                if (cur[i][y] == need){
                    int d = y - j;
                    if (d < bestd){
                        bestd = d; bestx = i; besty = y;
                    }
                }
            }
            // Search in rows below
            for (int x = i + 1; x < n; ++x){
                for (int y = 0; y < m; ++y){
                    if (cur[x][y] == need){
                        int d = (x - i) + abs(y - j);
                        if (d < bestd){
                            bestd = d; bestx = x; besty = y;
                        }
                    }
                }
            }
            // Move along planned path
            int x = bestx, y = besty;
            if (x == i){
                while (y > j){
                    // swap (i,y) with (i,y-1): op -2 i+1 y+1
                    addop(-2, i+1, y+1);
                    swap(cur[i][y], cur[i][y-1]);
                    y--;
                }
            } else {
                int t = max(y, j);
                while (y < t){
                    // swap (x,y) with (x,y+1): op -1 x+1 y+1
                    addop(-1, x+1, y+1);
                    swap(cur[x][y], cur[x][y+1]);
                    y++;
                }
                while (x > i){
                    // swap (x,y) with (x-1,y): op -3 x+1 y+1
                    addop(-3, x+1, y+1);
                    swap(cur[x][y], cur[x-1][y]);
                    x--;
                }
                while (y > j){
                    // swap (i,y) with (i,y-1): op -2 i+1 y+1
                    addop(-2, x+1, y+1);
                    swap(cur[x][y], cur[x][y-1]);
                    y--;
                }
            }
        }
    }
    
    cout << ops.size() << "\n";
    for (auto &op : ops){
        cout << op[0] << " " << op[1] << " " << op[2] << "\n";
    }
    return 0;
}