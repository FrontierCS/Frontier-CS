#include <bits/stdc++.h>
using namespace std;

static const int N = 10;

long long component_score(const array<array<int,N>,N>& b){
    bool vis[N][N] = {};
    long long score = 0;
    int dr[4] = {-1,1,0,0};
    int dc[4] = {0,0,-1,1};
    for(int r=0;r<N;r++){
        for(int c=0;c<N;c++){
            if(b[r][c]==0 || vis[r][c]) continue;
            int col = b[r][c];
            queue<pair<int,int>> q;
            q.push({r,c});
            vis[r][c]=true;
            int sz=0;
            while(!q.empty()){
                auto [rr,cc]=q.front(); q.pop();
                sz++;
                for(int k=0;k<4;k++){
                    int nr=rr+dr[k], nc=cc+dc[k];
                    if(nr<0||nr>=N||nc<0||nc>=N) continue;
                    if(vis[nr][nc]) continue;
                    if(b[nr][nc]==col){
                        vis[nr][nc]=true;
                        q.push({nr,nc});
                    }
                }
            }
            score += 1LL*sz*sz;
        }
    }
    return score;
}

array<array<int,N>,N> tilt_board(const array<array<int,N>,N>& b, char dir){
    array<array<int,N>,N> a = {};
    if(dir=='F'){
        for(int c=0;c<N;c++){
            int idx=0;
            for(int r=0;r<N;r++){
                if(b[r][c]!=0) a[idx++][c]=b[r][c];
            }
        }
    }else if(dir=='B'){
        for(int c=0;c<N;c++){
            int idx=N-1;
            for(int r=N-1;r>=0;r--){
                if(b[r][c]!=0) a[idx--][c]=b[r][c];
            }
        }
    }else if(dir=='L'){
        for(int r=0;r<N;r++){
            int idx=0;
            for(int c=0;c<N;c++){
                if(b[r][c]!=0) a[r][idx++]=b[r][c];
            }
        }
    }else{ // 'R'
        for(int r=0;r<N;r++){
            int idx=N-1;
            for(int c=N-1;c>=0;c--){
                if(b[r][c]!=0) a[r][idx--]=b[r][c];
            }
        }
    }
    return a;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    vector<int> f(100);
    for(int i=0;i<100;i++) if(!(cin>>f[i])) return 0;

    array<array<int,N>,N> board = {};
    for(int t=0;t<100;t++){
        int p; if(!(cin>>p)) return 0;
        // place candy at p-th empty cell (row-major: front-to-back, left-to-right)
        int cnt=0, pr=-1, pc=-1;
        for(int r=0;r<N;r++){
            for(int c=0;c<N;c++){
                if(board[r][c]==0){
                    cnt++;
                    if(cnt==p){
                        pr=r; pc=c;
                        r=N; break;
                    }
                }
            }
        }
        if(pr>=0) board[pr][pc]=f[t];

        // choose best direction
        const string dirs = "FBLR";
        long long bestScore = LLONG_MIN;
        char bestDir = 'F';
        int bestMove = INT_MAX;

        for(char d: dirs){
            auto nb = tilt_board(board, d);
            long long sc = component_score(nb);
            // movement count: positions unchanged with same value
            int unchanged = 0, filled = 0;
            for(int r=0;r<N;r++){
                for(int c=0;c<N;c++){
                    if(nb[r][c]>0) filled++;
                    if(nb[r][c]>0 && nb[r][c]==board[r][c]) unchanged++;
                }
            }
            int moved = filled - unchanged;
            if(sc > bestScore || (sc==bestScore && moved < bestMove)){
                bestScore = sc;
                bestDir = d;
                bestMove = moved;
            }
        }

        cout << bestDir << '\n' << flush;
        board = tilt_board(board, bestDir);
    }
    return 0;
}