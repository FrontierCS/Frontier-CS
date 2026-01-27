#include <bits/stdc++.h>
using namespace std;

struct Piece {
    int k;
    vector<pair<int,int>> cells;
    // chosen transform
    int R=0, F=0;
    int minx=0, miny=0, maxx=0, maxy=0;
    int w=0, h=0;
};

static inline pair<int,int> rot90(pair<int,int> p) { return {p.second, -p.first}; }

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin>>n)) return 0;
    vector<Piece> pieces(n);
    long long total_cells = 0;
    for(int i=0;i<n;i++){
        int k; cin>>k;
        pieces[i].k = k;
        pieces[i].cells.resize(k);
        for(int j=0;j<k;j++){
            int x,y; cin>>x>>y;
            pieces[i].cells[j]={x,y};
        }
        total_cells += k;
    }

    // Choose orientation for each piece: minimize height, then width
    long long total_bbox_area = 0;
    int max_wh = 1;
    for(int i=0;i<n;i++){
        Piece &pc = pieces[i];
        int bestR=0,bestF=0;
        int best_w=0,best_h=0,bminx=0,bminy=0,bmaxx=0,bmaxy=0;
        bool first=true;
        for(int F=0;F<=1;F++){
            vector<pair<int,int>> tmp = pc.cells;
            if(F){
                for(auto &p: tmp) p.first = -p.first;
            }
            for(int R=0;R<4;R++){
                if(R){
                    for(auto &p: tmp) p = rot90(p);
                }
                int minx=INT_MAX,miny=INT_MAX,maxx=INT_MIN,maxy=INT_MIN;
                for(auto &p: tmp){
                    minx=min(minx,p.first);
                    miny=min(miny,p.second);
                    maxx=max(maxx,p.first);
                    maxy=max(maxy,p.second);
                }
                int w = maxx-minx+1;
                int h = maxy-miny+1;
                if(first || h < best_h || (h==best_h && w < best_w)){
                    first=false;
                    best_h=h; best_w=w;
                    bestR=R; bestF=F;
                    bminx=minx; bminy=miny; bmaxx=maxx; bmaxy=maxy;
                }
            }
        }
        pc.R=bestR; pc.F=bestF;
        pc.minx=bminx; pc.miny=bminy; pc.maxx=bmaxx; pc.maxy=bmaxy;
        pc.w=best_w; pc.h=best_h;
        total_bbox_area += 1LL*pc.w*pc.h;
        max_wh = max(max_wh, max(pc.w, pc.h));
    }

    // Pack in square W=H=L using shelf algorithm on bounding boxes
    auto try_pack = [&](int L, vector<tuple<int,int,int,int>>& out)->bool{
        out.assign(n, {0,0,0,0});
        int cx=0, cy=0, rowH=0;
        for(int i=0;i<n;i++){
            int w=pieces[i].w, h=pieces[i].h;
            if(w>L || h>L) return false;
            if(cx + w > L){
                cy += rowH;
                cx = 0;
                rowH = 0;
            }
            if(cy + h > L) return false;
            int start_x = cx;
            int start_y = cy;
            int X = start_x - pieces[i].minx;
            int Y = start_y - pieces[i].miny;
            out[i] = {X, Y, pieces[i].R, pieces[i].F};
            cx += w;
            rowH = max(rowH, h);
        }
        return true;
    };

    int L = max(max_wh, (int)ceil(sqrt((double)max(1LL,total_bbox_area))));
    // small slack to reduce retries
    L = max(L, (int)ceil(sqrt((double)max(1LL,total_cells))));
    vector<tuple<int,int,int,int>> placement;
    // Increase geometrically until success
    for(int iter=0; iter<50; iter++){
        if(try_pack(L, placement)) break;
        long long lower = max<long long>(max_wh, (long long)ceil(sqrt((double)total_bbox_area)));
        L = (int)max<long long>((long long)L*3/2 + 1, lower);
    }
    // Final ensure success by linear growth if needed
    while(!try_pack(L, placement)) L++;

    cout<<L<<" "<<L<<"\n";
    for(int i=0;i<n;i++){
        auto [X,Y,R,F]=placement[i];
        cout<<X<<" "<<Y<<" "<<R<<" "<<F<<"\n";
    }
    return 0;
}