#include <bits/stdc++.h>
using namespace std;

struct Task {
    int id;
    int ax, ay, cx, cy;
    int tind;
};

static inline int manhattan(int x1,int y1,int x2,int y2){ return abs(x1-x2)+abs(y1-y2); }

long long route_cost_from_points(const vector<pair<int,int>>& pts){
    long long T=0;
    for(size_t i=0;i+1<pts.size();++i){
        T += manhattan(pts[i].first, pts[i].second, pts[i+1].first, pts[i+1].second);
    }
    return T;
}

long long pair_route_cost(const vector<int>& order, const vector<Task>& tasks){
    int x=400,y=400;
    long long T=0;
    for(int id: order){
        const Task& t = tasks[id];
        T += manhattan(x,y,t.ax,t.ay);
        x=t.ax; y=t.ay;
        T += manhattan(x,y,t.cx,t.cy);
        x=t.cx; y=t.cy;
    }
    T += manhattan(x,y,400,400);
    return T;
}

vector<pair<int,int>> build_pair_route(const vector<int>& order, const vector<Task>& tasks){
    vector<pair<int,int>> pts;
    pts.reserve(2*order.size()+2);
    pts.emplace_back(400,400);
    for(int id: order){
        const Task& t = tasks[id];
        pts.emplace_back(t.ax,t.ay);
        pts.emplace_back(t.cx,t.cy);
    }
    pts.emplace_back(400,400);
    return pts;
}

vector<int> build_greedy_order(const vector<int>& pool, const vector<Task>& tasks, int m, mt19937& rng){
    const int S = min<int>(pool.size(), 1000000);
    vector<char> used(tasks.size(), 0);
    vector<int> order; order.reserve(m);
    const int sStart = 7;
    const int sNext = 7;

    // choose start
    vector<pair<int,int>> cands;
    cands.reserve(S);
    for(int idx=0; idx<S; ++idx){
        int id = pool[idx];
        const Task& t = tasks[id];
        int cost = manhattan(400,400,t.ax,t.ay) + manhattan(t.cx,t.cy,400,400);
        cands.emplace_back(cost, id);
    }
    sort(cands.begin(), cands.end());
    int pickCount = min<int>(sStart, cands.size());
    uniform_int_distribution<int> distStart(0, pickCount-1);
    int chosen = cands[distStart(rng)].second;
    order.push_back(chosen);
    used[chosen] = 1;

    // subsequent picks
    for(int k=1; k<m; ++k){
        const Task& prev = tasks[order.back()];
        vector<pair<int,int>> cands2;
        cands2.reserve(S);
        for(int idx=0; idx<S; ++idx){
            int id = pool[idx];
            if(used[id]) continue;
            const Task& t = tasks[id];
            int cost = manhattan(prev.cx, prev.cy, t.ax, t.ay);
            cands2.emplace_back(cost, id);
        }
        if(cands2.empty()){
            // fallback: select any unused task (should not happen if pool size >= m)
            for(int id=0; id<(int)tasks.size(); ++id){
                if(!used[id]){
                    cands2.emplace_back(0,id);
                }
            }
        }
        sort(cands2.begin(), cands2.end());
        int take = min<int>(sNext, cands2.size());
        uniform_int_distribution<int> distNext(0, take-1);
        int chosen2 = cands2[distNext(rng)].second;
        order.push_back(chosen2);
        used[chosen2] = 1;
    }
    return order;
}

void two_opt_improve(vector<int>& order, const vector<Task>& tasks, long long& bestT, const chrono::steady_clock::time_point& deadline){
    int m = (int)order.size();
    bestT = pair_route_cost(order, tasks);
    bool improved = true;
    while(improved){
        if(chrono::steady_clock::now() > deadline) break;
        improved = false;
        for(int i=0;i<m;i++){
            for(int j=i+1;j<m;j++){
                if(chrono::steady_clock::now() > deadline) break;
                reverse(order.begin()+i, order.begin()+j+1);
                long long T = pair_route_cost(order, tasks);
                if(T < bestT){
                    bestT = T;
                    improved = true;
                    goto NEXT_ITER;
                }else{
                    reverse(order.begin()+i, order.begin()+j+1);
                }
            }
        }
        NEXT_ITER:;
    }
}

vector<pair<int,int>> build_greedy_event_route(const vector<int>& selected, const vector<Task>& tasks){
    // status: 0 not picked, 1 picked not delivered, 2 completed
    unordered_map<int,int> status;
    status.reserve(selected.size()*2);
    for(int id: selected) status[id]=0;
    int remaining = (int)selected.size();
    vector<pair<int,int>> route;
    route.emplace_back(400,400);
    int curx=400, cury=400;
    while(remaining>0){
        int bestId = -1;
        bool bestIsPickup = true;
        int bestD = INT_MAX;

        // Deliveries first if closer in tie
        for(int id: selected){
            int st = status[id];
            const Task& t = tasks[id];
            if(st==1){
                int d = manhattan(curx, cury, t.cx, t.cy);
                if(d < bestD || (d==bestD && !bestIsPickup)){
                    bestD = d;
                    bestId = id;
                    bestIsPickup = false;
                }
            }
        }
        for(int id: selected){
            int st = status[id];
            const Task& t = tasks[id];
            if(st==0){
                int d = manhattan(curx, cury, t.ax, t.ay);
                if(d < bestD){
                    bestD = d;
                    bestId = id;
                    bestIsPickup = true;
                }
            }
        }
        if(bestId==-1){
            // should not happen, but to be safe, pick any remaining delivery
            for(int id: selected){
                if(status[id]!=2){
                    const Task& t = tasks[id];
                    int d = manhattan(curx, cury, t.ax, t.ay);
                    if(d < bestD){
                        bestD = d; bestId=id; bestIsPickup=true;
                    }
                }
            }
            if(bestId==-1) break;
        }
        const Task& t = tasks[bestId];
        if(bestIsPickup){
            route.emplace_back(t.ax, t.ay);
            curx = t.ax; cury = t.ay;
            status[bestId] = 1;
        }else{
            route.emplace_back(t.cx, t.cy);
            curx = t.cx; cury = t.cy;
            status[bestId] = 2;
            remaining--;
        }
    }
    if(route.back().first!=400 || route.back().second!=400) route.emplace_back(400,400);
    return route;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    vector<Task> tasks;
    tasks.reserve(N);

    for(int i=0;i<N;i++){
        int a,b,c,d;
        if(!(cin>>a>>b>>c>>d)) return 0;
        Task t;
        t.id=i;
        t.ax=a; t.ay=b; t.cx=c; t.cy=d;
        t.tind = manhattan(400,400,a,b) + manhattan(a,b,c,d) + manhattan(c,d,400,400);
        tasks.push_back(t);
    }

    vector<int> idx(N);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j){
        if(tasks[i].tind != tasks[j].tind) return tasks[i].tind < tasks[j].tind;
        // tie-break by closeness to center to/from
        int wi = manhattan(400,400,tasks[i].ax,tasks[i].ay) + manhattan(400,400,tasks[i].cx,tasks[i].cy);
        int wj = manhattan(400,400,tasks[j].ax,tasks[j].ay) + manhattan(400,400,tasks[j].cx,tasks[j].cy);
        return wi < wj;
    });

    int P = min(300, N);
    vector<int> pool(idx.begin(), idx.begin()+P);

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto startTime = chrono::steady_clock::now();
    auto deadline = startTime + chrono::milliseconds(1800);

    // Initialize with deterministic order: first 50
    int M = 50;
    vector<int> bestOrder(pool.begin(), pool.begin()+M);
    long long bestPairT = pair_route_cost(bestOrder, tasks);

    // improve deterministic with greedy and 2-opt
    {
        vector<int> order = bestOrder;
        long long Tcur = bestPairT;
        two_opt_improve(order, tasks, Tcur, deadline);
        if(Tcur < bestPairT){
            bestPairT = Tcur;
            bestOrder = order;
        }
    }

    // Randomized attempts
    while(chrono::steady_clock::now() < deadline){
        vector<int> order = build_greedy_order(pool, tasks, M, rng);
        long long Tcur = pair_route_cost(order, tasks);
        if(Tcur < bestPairT){
            bestPairT = Tcur;
            bestOrder = order;
        }
        // 2-opt fine-tune with time check
        two_opt_improve(order, tasks, Tcur, deadline);
        if(Tcur < bestPairT){
            bestPairT = Tcur;
            bestOrder = order;
        }
    }

    // Build 100-node greedy route with same set of tasks
    vector<int> selected = bestOrder;
    sort(selected.begin(), selected.end());
    vector<pair<int,int>> route_pair = build_pair_route(bestOrder, tasks);
    long long T_pair = route_cost_from_points(route_pair);

    vector<pair<int,int>> route_event = build_greedy_event_route(selected, tasks);
    long long T_event = route_cost_from_points(route_event);

    vector<pair<int,int>> final_route;
    if(T_event < T_pair){
        final_route = route_event;
    }else{
        final_route = route_pair;
    }

    // Output
    cout << M;
    for(int id: selected){
        cout << " " << (id+1);
    }
    cout << "\n";
    cout << final_route.size();
    for(auto &p: final_route){
        cout << " " << p.first << " " << p.second;
    }
    cout << "\n";

    return 0;
}