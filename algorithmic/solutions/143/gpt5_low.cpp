#include <bits/stdc++.h>
using namespace std;

static const long long RATE_BUDGET_LIMIT = 3000000;
long long rate_used = 0;

double clamp01(double x){ return x<0?0:(x>1?1:x); }

// Simple deterministic pseudo-random generator based on state info
uint64_t mix64(uint64_t x){
    x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL;
    x ^= x >> 27; x *= 0x94d049bb133111ebULL;
    x ^= x >> 31;
    return x;
}
double detRand(int h,int r, const vector<int>& cards){
    uint64_t s = 0x9e3779b97f4a7c15ULL;
    s ^= (uint64_t)h + 0x9e3779b97f4a7c15ULL + (s<<6) + (s>>2);
    s ^= (uint64_t)r + 0x9e3779b97f4a7c15ULL + (s<<6) + (s>>2);
    for(int x:cards){
        s ^= (uint64_t)x + 0x9e3779b97f4a7c15ULL + (s<<6) + (s>>2);
    }
    uint64_t v = mix64(s);
    return (v >> 11) * (1.0 / 9007199254740992.0); // [0,1)
}

int plannedT(int r){
    // rounds 1..4
    if(r==1) return 30;
    if(r==2) return 60;
    if(r==3) return 80;
    return 120;
}

int request_rate(int t, double &w, double &d){
    if(t<=0) { w=0.5; d=0.0; return 0; }
    cout << "RATE " << t << endl;
    cout.flush();
    string tok;
    if(!(cin>>tok)) return -1;
    if(tok=="-1") return -1;
    if(tok!="RATES"){
        // Protocol violation, try to read until -1 or exit
        return -1;
    }
    if(!(cin>>w>>d)) return -1;
    return 0;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int G;
    if(!(cin>>G)) return 0;
    if(G==-1) return 0;

    string tok;
    while(cin>>tok){
        if(tok=="-1") break;
        if(tok=="STATE"){
            int h,r,a,b,P,k;
            if(!(cin>>h>>r>>a>>b>>P>>k)) return 0;
            string al;
            cin>>al; // "ALICE"
            int s1,v1,s2,v2;
            cin>>s1>>v1>>s2>>v2;
            string brd;
            cin>>brd; // "BOARD"
            vector<pair<int,int>> board;
            for(int i=0;i<k;i++){
                int cs, cv; cin>>cs>>cv;
                board.push_back({cs,cv});
            }

            // Decide whether to query RATE
            int tplan = plannedT(r);
            long long remaining = RATE_BUDGET_LIMIT - rate_used;
            if(remaining < 0) remaining = 0;
            // leave some safety buffer for remaining states; scale down
            int t = (int)min<long long>(tplan, max<long long>(0, remaining - 1000));
            double w=0.5,d=0.0;
            if(t>0){
                if(request_rate(t,w,d)==-1) return 0;
                rate_used += t;
            }else{
                // fallback: very rough heuristic equity by hole cards
                // Pair strong, suited/connectors marginal
                bool pair = (v1==v2);
                bool suited = (s1==s2);
                int gap = abs(v1 - v2);
                double e = 0.5;
                if(pair){
                    if(v1>=11) e=0.67;
                    else if(v1>=8) e=0.60;
                    else e=0.56;
                }else{
                    if(suited && gap<=2) e=0.53;
                    else if(gap<=1) e=0.52;
                    else if(suited) e=0.51;
                    else e=0.49;
                }
                w = e; d = 0.0;
            }
            double equity = clamp01(w + 0.5*d);

            // Determine action
            // We never FOLD since CHECK is always allowed and opponent won't bet unless we raise.
            // Raise sizing
            int baseX = max(1, min(a, max(1, P/2)));
            int x = baseX;

            // Deterministic bluff decision
            vector<int> cv;
            cv.push_back(s1); cv.push_back(v1); cv.push_back(s2); cv.push_back(v2);
            for(auto &p:board){ cv.push_back(p.first); cv.push_back(p.second); }
            double rnd = detRand(h,r,cv);

            bool doRaise = false;
            if(equity > 0.64){
                doRaise = true;
                if(r==4){
                    x = min(a, max(baseX, P)); // bigger on river
                }else{
                    x = baseX;
                }
            }else if(equity > 0.58){
                doRaise = true;
                x = baseX;
            }else if(equity < 0.36){
                double p = (equity<0.30)?0.35:0.18;
                if(rnd < p){
                    doRaise = true;
                    x = max(1, min(a, max(1, P/3)));
                }
            }

            // If very short stack and good equity, raise bigger
            if(doRaise && a<=10 && equity>0.56){
                x = min(a, max(x, min(a, P))); // push more when short
            }

            if(doRaise && x>=1 && x<=a){
                cout << "ACTION RAISE " << x << endl;
            }else{
                cout << "ACTION CHECK" << endl;
            }
            cout.flush();
        }else if(tok=="OPP"){
            string what; cin>>what;
            if(what=="FOLD"){
                // hand ends immediately; RESULT next
            }else if(what=="CALL"){
                int x; cin>>x;
            }else if(what=="CHECK"){
                // nothing
            }
        }else if(tok=="RESULT"){
            int delta; cin>>delta;
            // end of hand
        }else if(tok=="SCORE"){
            double W; cin>>W;
            // match ends
            // We can exit gracefully
            // But continue to allow judge to close
        }else if(tok=="RATES"){
            // Unexpected; read and ignore
            double w,d; cin>>w>>d;
        }else if(tok=="BOARD"){
            // Should only appear after STATE parsing; but handle gracefully by consuming unknown k? Skip line
            // Not expected here.
        }else{
            // Unknown token; try to continue
        }
    }
    return 0;
}