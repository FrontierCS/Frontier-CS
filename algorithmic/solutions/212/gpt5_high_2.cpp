#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n,m,L,R,Sx,Sy,Lq;
    long long s;
    if(!(cin>>n>>m>>L>>R>>Sx>>Sy>>Lq>>s)) return 0;
    vector<int> q(Lq);
    for(int i=0;i<Lq;i++) cin>>q[i];
    // Basic validation
    for(int x: q){
        if(x<1 || x>n){
            cout<<"NO\n";
            return 0;
        }
    }
    auto isSubseq = [&](const vector<int>& O)->bool{
        int j=0;
        for(int x: O){
            if(j<Lq && x==q[j]) j++;
        }
        return j==Lq;
    };
    auto buildOrder = [&](int d0, int secondOrder)->vector<int>{
        vector<int> O;
        if(d0==+1){
            for(int x=Sx;x<=n;x++) O.push_back(x);
            if(Sx>1){
                if(secondOrder==+1){
                    for(int x=1;x<=Sx-1;x++) O.push_back(x);
                }else{
                    for(int x=Sx-1;x>=1;x--) O.push_back(x);
                }
            }
        }else{ // d0 == -1
            for(int x=Sx;x>=1;x--) O.push_back(x);
            if(Sx<n){
                if(secondOrder==+1){
                    for(int x=Sx+1;x<=n;x++) O.push_back(x);
                }else{
                    for(int x=n;x>=Sx+1;x--) O.push_back(x);
                }
            }
        }
        return O;
    };
    auto feasible = [&](int d0, int secondOrder)->bool{
        bool leftAvail = (L>1);
        bool rightAvail = (R<m);
        int width = R-L+1;
        int boundary = (d0==+1? n : 1);
        bool secondExists = (d0==+1? (Sx>1) : (Sx<n));
        if(!secondExists) return true; // no need to exit
        if(!leftAvail && !rightAvail) return false;
        // End column at boundary
        char endCol;
        if(width==1){
            // can exit to any available side
            return leftAvail || rightAvail;
        }else{
            int par = abs(boundary - Sx)%2; // 0 -> end at R, 1 -> end at L
            endCol = (par==0? 'R' : 'L');
            if(endCol=='L') return leftAvail;
            else return rightAvail;
        }
    };
    // Try 4 scenarios: (d0 in {+1,-1}) x (secondOrder in {+1,-1})
    struct Plan {int d0; int secondOrder;};
    vector<Plan> candidates;
    candidates.push_back({+1,+1});
    candidates.push_back({+1,-1});
    candidates.push_back({-1,+1});
    candidates.push_back({-1,-1});
    Plan chosen = {0,0};
    bool found=false;
    for(auto pl: candidates){
        if(!feasible(pl.d0, pl.secondOrder)) continue;
        auto O = buildOrder(pl.d0, pl.secondOrder);
        if(isSubseq(O)){
            chosen = pl;
            found = true;
            break;
        }
    }
    if(!found){
        cout<<"NO\n";
        return 0;
    }
    // Generate path for chosen plan
    int d0 = chosen.d0, secondOrder = chosen.secondOrder;
    vector<pair<int,int>> ans;
    vector<vector<bool>> vis(n+1, vector<bool>(m+1,false));
    auto add = [&](int x,int y)->void{
        ans.emplace_back(x,y);
        vis[x][y]=true;
    };
    auto horizLR = [&](int x, int yStart, int yEnd)->void{
        if(yStart<=yEnd){
            for(int y=yStart;y<=yEnd;y++){
                if(!vis[x][y]) add(x,y);
            }
        }else{
            for(int y=yStart;y>=yEnd;y--){
                if(!vis[x][y]) add(x,y);
            }
        }
    };
    auto stepTo = [&](int nx,int ny)->void{
        if(!vis[nx][ny]) add(nx,ny);
    };
    // Start at (Sx, L)
    add(Sx, L);
    // Traverse row Sx from L to R
    if(R>=L+1){
        for(int y=L+1;y<=R;y++) stepTo(Sx,y);
    }
    int curx=Sx, cury=R;
    // First block along strip towards boundary
    if(d0==+1){
        for(int x=Sx+1;x<=n;x++){
            // move down in current column
            stepTo(x, cury);
            // traverse row x
            if(cury==R){
                // go R -> L
                for(int y=R-1;y>=L;y--) stepTo(x,y);
                cury=L;
            }else{
                // go L -> R
                for(int y=L+1;y<=R;y++) stepTo(x,y);
                cury=R;
            }
            curx=x;
        }
    }else{
        for(int x=Sx-1;x>=1;x--){
            // move up in current column
            stepTo(x, cury);
            // traverse row x
            if(cury==R){
                for(int y=R-1;y>=L;y--) stepTo(x,y);
                cury=L;
            }else{
                for(int y=L+1;y<=R;y++) stepTo(x,y);
                cury=R;
            }
            curx=x;
        }
    }
    // Determine second block and outside movement if exists
    bool secondExists = (d0==+1? (Sx>1) : (Sx<n));
    if(secondExists){
        bool leftAvail = (L>1), rightAvail = (R<m);
        int width = R-L+1;
        // Decide side to exit
        int side = -1; // 0 left, 1 right
        if(width==1){
            if(rightAvail) side=1;
            else side=0;
        }else{
            if(cury==L) side=0;
            else side=1;
        }
        int outsideCol = (side==0? L-1 : R+1);
        // step to outside
        stepTo(curx, outsideCol);
        // Determine re-entry row r0 and iterate
        int r0, rend, step;
        if(d0==+1){
            if(secondOrder==+1){ r0=1; rend=Sx-1; step=+1; }
            else { r0=Sx-1; rend=1; step=-1; }
        }else{
            if(secondOrder==+1){ r0=Sx+1; rend=n; step=+1; }
            else { r0=n; rend=Sx+1; step=-1; }
        }
        // Move along outside to r0
        if(curx<r0){
            for(int x=curx+1;x<=r0;x++) stepTo(x, outsideCol);
        }else{
            for(int x=curx-1;x>=r0;x--) stepTo(x, outsideCol);
        }
        // Enter at side into row r0
        if(side==0){
            stepTo(r0, L);
            // traverse L->R
            for(int y=L+1;y<=R;y++) stepTo(r0,y);
            cury=R;
        }else{
            stepTo(r0, R);
            // traverse R->L
            for(int y=R-1;y>=L;y--) stepTo(r0,y);
            cury=L;
        }
        curx=r0;
        // Process remaining rows in this block
        for(int x=curx+step; (step==+1? x<=rend : x>=rend); x+=step){
            // move vertically within strip
            stepTo(x, cury);
            if(cury==R){
                for(int y=R-1;y>=L;y--) stepTo(x,y);
                cury=L;
            }else{
                for(int y=L+1;y<=R;y++) stepTo(x,y);
                cury=R;
            }
            curx=x;
        }
    }
    cout<<"YES\n";
    cout<<ans.size()<<"\n";
    for(auto &p: ans){
        cout<<p.first<<" "<<p.second<<"\n";
    }
    return 0;
}