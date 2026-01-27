#include <bits/stdc++.h>
using namespace std;

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    const long long BASE = 100001LL;
    unordered_set<long long> pts;
    pts.reserve(2*N*2);
    pts.max_load_factor(0.7);
    for(int i=0;i<2*N;i++){
        int x,y; cin>>x>>y;
        pts.insert((long long)x*BASE + y);
    }
    int ax=0, ay=0;
    bool found=false;
    // Try a simple scan; should find very quickly
    const int MAXC = 100000;
    for(int x=0; x<=MAXC-1 && !found; x+=137){
        for(int y=0; y<=MAXC-1 && !found; y+=131){
            long long c1 = (long long)x*BASE + y;
            long long c2 = (long long)(x+1)*BASE + y;
            long long c3 = (long long)(x+1)*BASE + (y+1);
            long long c4 = (long long)x*BASE + (y+1);
            if(pts.find(c1)==pts.end() &&
               pts.find(c2)==pts.end() &&
               pts.find(c3)==pts.end() &&
               pts.find(c4)==pts.end()){
                ax = x; ay = y; found=true; break;
            }
        }
    }
    if(!found){
        // Fallback exhaustive scan in small area
        for(int x=0; x<=MAXC-1 && !found; x++){
            for(int y=0; y<=MAXC-1 && !found; y++){
                long long c1 = (long long)x*BASE + y;
                long long c2 = (long long)(x+1)*BASE + y;
                long long c3 = (long long)(x+1)*BASE + (y+1);
                long long c4 = (long long)x*BASE + (y+1);
                if(pts.find(c1)==pts.end() &&
                   pts.find(c2)==pts.end() &&
                   pts.find(c3)==pts.end() &&
                   pts.find(c4)==pts.end()){
                    ax = x; ay = y; found=true; break;
                }
            }
        }
    }
    // Output a small 1x1 rectangle
    cout << 4 << '\n';
    cout << ax << ' ' << ay << '\n';
    cout << ax+1 << ' ' << ay << '\n';
    cout << ax+1 << ' ' << ay+1 << '\n';
    cout << ax << ' ' << ay+1 << '\n';
    return 0;
}