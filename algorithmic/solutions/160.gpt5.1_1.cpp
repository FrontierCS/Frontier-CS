#include <bits/stdc++.h>
using namespace std;

struct Board {
    int g[10][10];
    Board() { memset(g, 0, sizeof(g)); }
};

void tiltF(Board &b){
    for(int c=0;c<10;++c){
        int ptr=0;
        for(int r=0;r<10;++r){
            if(b.g[r][c]!=0){
                if(r!=ptr){
                    b.g[ptr][c]=b.g[r][c];
                    b.g[r][c]=0;
                }
                ++ptr;
            }
        }
    }
}
void tiltB(Board &b){
    for(int c=0;c<10;++c){
        int ptr=9;
        for(int r=9;r>=0;--r){
            if(b.g[r][c]!=0){
                if(r!=ptr){
                    b.g[ptr][c]=b.g[r][c];
                    b.g[r][c]=0;
                }
                --ptr;
            }
        }
    }
}
void tiltL(Board &b){
    for(int r=0;r<10;++r){
        int ptr=0;
        for(int c=0;c<10;++c){
            if(b.g[r][c]!=0){
                if(c!=ptr){
                    b.g[r][ptr]=b.g[r][c];
                    b.g[r][c]=0;
                }
                ++ptr;
            }
        }
    }
}
void tiltR(Board &b){
    for(int r=0;r<10;++r){
        int ptr=9;
        for(int c=9;c>=0;--c){
            if(b.g[r][c]!=0){
                if(c!=ptr){
                    b.g[r][ptr]=b.g[r][c];
                    b.g[r][c]=0;
                }
                --ptr;
            }
        }
    }
}
void tilt(Board &b, char dir){
    if(dir=='F') tiltF(b);
    else if(dir=='B') tiltB(b);
    else if(dir=='L') tiltL(b);
    else if(dir=='R') tiltR(b);
}

int evalBoard(const Board &b){
    bool vis[10][10]={false};
    static const int dr[4]={-1,1,0,0};
    static const int dc[4]={0,0,-1,1};
    int res=0;
    for(int i=0;i<10;++i){
        for(int j=0;j<10;++j){
            if(!vis[i][j] && b.g[i][j]!=0){
                int color=b.g[i][j];
                int sz=0;
                queue<pair<int,int>> q;
                q.push({i,j});
                vis[i][j]=true;
                while(!q.empty()){
                    auto [r,c]=q.front(); q.pop();
                    ++sz;
                    for(int k=0;k<4;++k){
                        int nr=r+dr[k], nc=c+dc[k];
                        if(0<=nr && nr<10 && 0<=nc && nc<10 && !vis[nr][nc] && b.g[nr][nc]==color){
                            vis[nr][nc]=true;
                            q.push({nr,nc});
                        }
                    }
                }
                res += sz*sz;
            }
        }
    }
    return res;
}

void placeCandy(Board &b, int flavor, int p){
    int cnt=0;
    for(int r=0;r<10;++r){
        for(int c=0;c<10;++c){
            if(b.g[r][c]==0){
                ++cnt;
                if(cnt==p){
                    b.g[r][c]=flavor;
                    return;
                }
            }
        }
    }
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> flavor(100);
    for(int i=0;i<100;++i){
        if(!(cin>>flavor[i])) return 0;
    }

    Board cur;
    const char DIRS[4] = {'F','B','L','R'};

    for(int t=0;t<100;++t){
        int p;
        if(!(cin>>p)) return 0;

        placeCandy(cur, flavor[t], p);

        char bestDir='F';
        int bestScore=-1;

        for(int d=0; d<4; ++d){
            Board tmp = cur;
            tilt(tmp, DIRS[d]);
            int sc = evalBoard(tmp);
            if(sc > bestScore){
                bestScore = sc;
                bestDir = DIRS[d];
            }
        }

        cout << bestDir << '\n';
        cout.flush();

        tilt(cur, bestDir);
    }

    return 0;
}