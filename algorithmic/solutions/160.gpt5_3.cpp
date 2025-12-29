#include <bits/stdc++.h>
using namespace std;

using Board = array<array<int,10>,10>;

static inline Board tilt(const Board &b, char dir){
    Board a = {};
    if(dir=='F'){ // up
        for(int c=0;c<10;c++){
            int k=0;
            for(int r=0;r<10;r++) if(b[r][c]) a[k++][c]=b[r][c];
            for(int r=k;r<10;r++) a[r][c]=0;
        }
    }else if(dir=='B'){ // down
        for(int c=0;c<10;c++){
            int m=0;
            for(int r=0;r<10;r++) if(b[r][c]) m++;
            int base=10-m;
            for(int r=0;r<base;r++) a[r][c]=0;
            int idx=0;
            for(int r=0;r<10;r++) if(b[r][c]) a[base+idx++][c]=b[r][c];
        }
    }else if(dir=='L'){ // left
        for(int r=0;r<10;r++){
            int k=0;
            for(int c=0;c<10;c++) if(b[r][c]) a[r][k++]=b[r][c];
            for(int c=k;c<10;c++) a[r][c]=0;
        }
    }else{ // 'R' right
        for(int r=0;r<10;r++){
            int m=0;
            for(int c=0;c<10;c++) if(b[r][c]) m++;
            int base=10-m;
            for(int c=0;c<base;c++) a[r][c]=0;
            int idx=0;
            for(int c=0;c<10;c++) if(b[r][c]) a[r][base+idx++]=b[r][c];
        }
    }
    return a;
}

static inline long long scoreBoard(const Board &b){
    bool vis[10][10]={0};
    long long res=0;
    static int dr[4]={-1,1,0,0};
    static int dc[4]={0,0,-1,1};
    for(int r=0;r<10;r++){
        for(int c=0;c<10;c++){
            if(b[r][c]==0 || vis[r][c]) continue;
            int col=b[r][c];
            int sz=0;
            queue<pair<int,int>> q;
            q.push({r,c});
            vis[r][c]=true;
            while(!q.empty()){
                auto [rr,cc]=q.front(); q.pop();
                sz++;
                for(int k=0;k<4;k++){
                    int nr=rr+dr[k], nc=cc+dc[k];
                    if(nr<0||nr>=10||nc<0||nc>=10) continue;
                    if(!vis[nr][nc] && b[nr][nc]==col){
                        vis[nr][nc]=true;
                        q.push({nr,nc});
                    }
                }
            }
            res += 1LL*sz*sz;
        }
    }
    return res;
}

static inline pair<int,int> getEmptyCoord(const Board &b, int p){
    int cnt=0;
    for(int r=0;r<10;r++){
        for(int c=0;c<10;c++){
            if(b[r][c]==0){
                cnt++;
                if(cnt==p) return {r,c};
            }
        }
    }
    return {-1,-1}; // should not happen
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<int> f(100);
    for(int i=0;i<100;i++){
        if(!(cin>>f[i])) return 0;
    }
    Board board = {};
    const vector<char> dirs = {'L','F','R','B'}; // tie-break preference
    for(int t=0;t<100;t++){
        int p;
        if(!(cin>>p)) return 0;
        auto [r,c] = getEmptyCoord(board, p);
        if(r==-1){
            // should not happen, but safeguard
            cout << "F" << endl;
            cout.flush();
            continue;
        }
        Board withNew = board;
        withNew[r][c] = f[t];
        long long bestScore = LLONG_MIN;
        char bestDir = 'F';
        Board bestBoard = withNew;
        for(char d: dirs){
            Board nb = tilt(withNew, d);
            long long sc = scoreBoard(nb);
            if(sc > bestScore){
                bestScore = sc;
                bestDir = d;
                bestBoard = nb;
            }
        }
        cout << bestDir << endl;
        cout.flush();
        board = bestBoard;
    }
    return 0;
}