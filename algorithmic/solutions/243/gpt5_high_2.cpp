#include <bits/stdc++.h>
using namespace std;

struct Sig {
    int lab, l, r, s;
    bool operator==(const Sig& other) const {
        return lab==other.lab && l==other.l && r==other.r && s==other.s;
    }
};

struct SigHash {
    size_t operator()(Sig const& sg) const noexcept {
        size_t h = 1469598103934665603ull;
        auto mix = [&](int x){
            h ^= (uint64_t)(uint32_t)x + 0x9e3779b97f4a7c15ull + (h<<6) + (h>>2);
        };
        mix(sg.lab);
        mix(sg.l);
        mix(sg.r);
        mix(sg.s);
        return h;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int r,c;
    if(!(cin>>r>>c)) return 0;
    vector<string> grid(r);
    for(int i=0;i<r;i++) cin>>grid[i];
    const int dr[4] = {-1,0,1,0};
    const int dc[4] = {0,1,0,-1};
    
    // Map open cells to ids
    vector<vector<int>> cellId(r, vector<int>(c, -1));
    vector<pair<int,int>> id2pos;
    int nOpen = 0;
    for(int i=0;i<r;i++){
        for(int j=0;j<c;j++){
            if(grid[i][j]=='.'){
                cellId[i][j] = nOpen++;
                id2pos.push_back({i,j});
            }
        }
    }
    if(nOpen==0){
        // Should not happen per statement, but be safe
        // No possible start, terminate on first -1 if given
        int d;
        while(cin>>d){
            if(d==-1) return 0;
            cout<<"no"<<endl;
            return 0;
        }
        return 0;
    }
    int N = nOpen * 4; // states = (cell,dir)
    vector<int> distAhead(N, -1);
    vector<int> nextL(N, -1), nextR(N, -1), nextS(N, -1);
    vector<int> statePos(N, -1); // cell id of state
    
    auto inside = [&](int x, int y){ return x>=0 && x<r && y>=0 && y<c; };
    
    // Precompute distAhead and transitions
    for(int cid=0; cid<nOpen; ++cid){
        auto [i,j] = id2pos[cid];
        for(int dir=0; dir<4; ++dir){
            int sid = cid*4 + dir;
            statePos[sid] = cid;
            // Left/right rotations
            nextL[sid] = cid*4 + ((dir+3)&3);
            nextR[sid] = cid*4 + ((dir+1)&3);
            // distance ahead
            int cnt = 0;
            int x = i, y = j;
            while(true){
                int nx = x + dr[dir];
                int ny = y + dc[dir];
                if(!inside(nx,ny) || grid[nx][ny]=='#') break;
                cnt++;
                x = nx; y = ny;
            }
            distAhead[sid] = cnt;
            if(cnt>0){
                int nx = i + dr[dir];
                int ny = j + dc[dir];
                int nid = cellId[nx][ny];
                // nid should be valid
                nextS[sid] = nid*4 + dir;
            } else {
                nextS[sid] = -1;
            }
        }
    }
    
    // Compute global indistinguishability partition (bisimulation-like)
    // Initial partition by label (distAhead)
    vector<int> part(N, -1);
    // map label to group id
    unordered_map<int,int> lab2grp;
    lab2grp.reserve(128);
    int grpCnt = 0;
    for(int s=0; s<N; ++s){
        int lab = distAhead[s];
        auto it = lab2grp.find(lab);
        if(it==lab2grp.end()){
            lab2grp[lab] = grpCnt;
            part[s] = grpCnt++;
        } else {
            part[s] = it->second;
        }
    }
    // refine
    while(true){
        bool changed = false;
        unordered_map<Sig,int, SigHash> mp;
        mp.reserve(N*2);
        vector<int> newPart(N, -1);
        int newCnt = 0;
        for(int s=0; s<N; ++s){
            int lab = distAhead[s];
            int l = part[nextL[s]];
            int rdir = part[nextR[s]];
            int st = -1;
            if(lab>0){
                st = part[nextS[s]];
            }
            Sig sg{lab,l,rdir,st};
            auto it = mp.find(sg);
            if(it==mp.end()){
                mp.emplace(sg, newCnt);
                newPart[s] = newCnt++;
            } else {
                newPart[s] = it->second;
            }
        }
        if(newCnt != grpCnt) changed = true;
        else {
            for(int s=0; s<N; ++s){
                if(newPart[s]!=part[s]){ changed = true; break; }
            }
        }
        part.swap(newPart);
        grpCnt = newCnt;
        if(!changed) break;
    }
    // Check unsolvable: any group contains >1 distinct position
    vector<int> firstPos(grpCnt, -1);
    vector<char> multiPos(grpCnt, 0);
    for(int s=0; s<N; ++s){
        int g = part[s];
        int p = statePos[s];
        if(firstPos[g]==-1) firstPos[g] = p;
        else if(firstPos[g]!=p) multiPos[g] = 1;
    }
    bool unsolvable = false;
    for(int g=0; g<grpCnt; ++g){
        if(multiPos[g]) { unsolvable = true; break; }
    }
    
    // Initialize candidate states: all states
    vector<int> S;
    S.reserve(N);
    for(int s=0; s<N; ++s) S.push_back(s);
    
    auto unique_position = [&](const vector<int>& V)->int{
        if(V.empty()) return -1;
        int p = statePos[V[0]];
        for(size_t k=1;k<V.size();++k){
            if(statePos[V[k]]!=p) return -1;
        }
        return p;
    };
    
    auto apply_action = [&](vector<int>& V, const string& act){
        vector<int> W;
        W.reserve(V.size());
        if(act=="left"){
            for(int s: V) W.push_back(nextL[s]);
        } else if(act=="right"){
            for(int s: V) W.push_back(nextR[s]);
        } else if(act=="step"){
            for(int s: V) W.push_back(nextS[s]);
        }
        V.swap(W);
    };
    
    auto choose_action = [&](const vector<int>& V, int d)->string{
        // allowed actions: left/right always; step iff d>0
        struct Eval {
            string act;
            int worstPos;
            int worstStates;
            int diversity; // number of distinct buckets
            int pref; // tie-break preference (lower better)
        };
        vector<Eval> candidates;
        vector<string> acts = {"left","right"};
        if(d>0) acts.push_back("step");
        for(const string& act : acts){
            // compute bucket by next distance
            // Distances range 0..maxD ~ 100; we'll use unordered_map to be safe
            unordered_map<int,int> stateCounts;
            stateCounts.reserve(V.size()*2+1);
            unordered_map<int, unordered_set<int>> posSets;
            posSets.reserve(64);
            for(int s: V){
                int s2 = (act=="left"? nextL[s] : (act=="right"? nextR[s] : nextS[s]));
                int d2 = distAhead[s2];
                stateCounts[d2]++;
                auto &sett = posSets[d2];
                sett.insert(statePos[s2]);
            }
            int worstStates = 0;
            int worstPos = 0;
            int diversity = (int)stateCounts.size();
            for(auto &kv: stateCounts){
                worstStates = max(worstStates, kv.second);
            }
            for(auto &kv: posSets){
                worstPos = max(worstPos, (int)kv.second.size());
            }
            int pref = 2;
            if(act=="step") pref = 0;
            else if(act=="left") pref = 1;
            else pref = 2;
            candidates.push_back({act,worstPos,worstStates,diversity,pref});
        }
        // Choose best: minimize worstPos, then worstStates, then maximize diversity, then pref
        sort(candidates.begin(), candidates.end(), [&](const Eval& A, const Eval& B){
            if(A.worstPos != B.worstPos) return A.worstPos < B.worstPos;
            if(A.worstStates != B.worstStates) return A.worstStates < B.worstStates;
            if(A.diversity != B.diversity) return A.diversity > B.diversity;
            return A.pref < B.pref;
        });
        return candidates.front().act;
    };
    
    // Interaction loop
    while(true){
        int d;
        if(!(cin>>d)) break;
        if(d==-1) return 0;
        
        // Filter by current observation
        {
            vector<int> W;
            W.reserve(S.size());
            for(int s: S){
                if(distAhead[s]==d) W.push_back(s);
            }
            S.swap(W);
        }
        // If impossible in principle, claim "no"
        if(unsolvable){
            cout<<"no"<<endl;
            return 0;
        }
        // If unique position, claim yes
        int p = unique_position(S);
        if(p!=-1){
            int i = id2pos[p].first + 1;
            int j = id2pos[p].second + 1;
            cout<<"yes "<<i<<" "<<j<<endl;
            return 0;
        }
        // Choose action
        string act = choose_action(S, d);
        cout<<act<<endl;
        // Apply action to candidates
        apply_action(S, act);
    }
    return 0;
}