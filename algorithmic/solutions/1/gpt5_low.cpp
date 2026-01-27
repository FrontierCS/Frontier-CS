#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
};

struct Solution {
    vector<long long> x;
    long long value;
    long long remM, remL;
};

static const long long CAP_M = 20LL * 1000000LL; // mg
static const long long CAP_L = 25LL * 1000000LL; // uL

void skipSpaces(const string& s, size_t& i){
    while(i < s.size() && isspace((unsigned char)s[i])) i++;
}

bool parseString(const string& s, size_t& i, string& out){
    skipSpaces(s, i);
    if(i >= s.size() || s[i] != '"') return false;
    i++;
    string res;
    while(i < s.size() && s[i] != '"'){
        // no escape handling needed for given problem
        res.push_back(s[i]);
        i++;
    }
    if(i >= s.size() || s[i] != '"') return false;
    i++;
    out = res;
    return true;
}

bool parseInt(const string& s, size_t& i, long long& val){
    skipSpaces(s, i);
    bool neg = false;
    if(i < s.size() && (s[i] == '-' || s[i] == '+')){
        neg = (s[i]=='-');
        i++;
    }
    skipSpaces(s, i);
    if(i >= s.size() || !isdigit((unsigned char)s[i])) return false;
    long long v = 0;
    while(i < s.size() && isdigit((unsigned char)s[i])){
        v = v*10 + (s[i]-'0');
        i++;
    }
    val = neg ? -v : v;
    return true;
}

bool parseArray4(const string& s, size_t& i, array<long long,4>& arr){
    skipSpaces(s, i);
    if(i >= s.size() || s[i] != '[') return false;
    i++;
    for(int k=0;k<4;k++){
        skipSpaces(s, i);
        // potential newlines/commas
        long long x;
        if(!parseInt(s, i, x)) return false;
        arr[k]=x;
        skipSpaces(s, i);
        if(k<3){
            if(i >= s.size()) return false;
            // allow trailing commas and newlines/spaces
            if(s[i] == ','){ i++; }
        }
    }
    skipSpaces(s, i);
    // allow trailing commas/newlines inside array
    while(i < s.size() && s[i] != ']'){
        // consume potential commas or spaces/newlines
        if(s[i]==','){ i++; }
        else if(isspace((unsigned char)s[i])) i++;
        else break;
    }
    if(i >= s.size() || s[i] != ']') return false;
    i++;
    return true;
}

vector<Item> parseInput(const string& s){
    vector<Item> items;
    size_t i=0;
    skipSpaces(s,i);
    if(i<s.size() && s[i]=='{') i++;
    while(i < s.size()){
        skipSpaces(s,i);
        if(i < s.size() && s[i]=='}'){ i++; break; }
        string key;
        if(!parseString(s,i,key)) break;
        skipSpaces(s,i);
        if(i >= s.size() || s[i] != ':') break;
        i++;
        array<long long,4> arr;
        if(!parseArray4(s,i,arr)) break;
        items.push_back({key, arr[0], arr[1], arr[2], arr[3]});
        skipSpaces(s,i);
        if(i < s.size() && s[i]==','){ i++; continue; }
    }
    return items;
}

long long ceil_div(long long a, long long b){
    if (a <= 0) return 0;
    return (a + b - 1) / b;
}

Solution greedyFill(const vector<Item>& items, const vector<int>& order){
    int n = items.size();
    Solution sol;
    sol.x.assign(n,0);
    sol.remM = CAP_M;
    sol.remL = CAP_L;
    sol.value = 0;
    for(int idx : order){
        const auto& it = items[idx];
        if (it.m > CAP_M || it.l > CAP_L) continue;
        long long byM = sol.remM / it.m;
        long long byL = sol.remL / it.l;
        long long take = min({it.q, byM, byL});
        if(take <= 0) continue;
        sol.x[idx] += take;
        sol.remM -= take * it.m;
        sol.remL -= take * it.l;
        sol.value += take * it.v;
    }
    return sol;
}

void tryDirectFill(const vector<Item>& items, const vector<int>& order, Solution& sol){
    for(int idx : order){
        const auto& it = items[idx];
        if (it.m > CAP_M || it.l > CAP_L) continue;
        long long canq = it.q - sol.x[idx];
        if(canq <= 0) continue;
        long long byM = sol.remM / it.m;
        long long byL = sol.remL / it.l;
        long long take = min({canq, byM, byL});
        if(take <= 0) continue;
        sol.x[idx] += take;
        sol.remM -= take * it.m;
        sol.remL -= take * it.l;
        sol.value += take * it.v;
    }
}

bool improveOneSwap(const vector<Item>& items, Solution& sol){
    int n = items.size();
    // attempt adding one of item a, removing t of item b
    for(int a=0;a<n;a++){
        const auto& ia = items[a];
        if(sol.x[a] >= ia.q) continue;
        if (ia.m > CAP_M || ia.l > CAP_L) continue;
        long long needM = max(0LL, ia.m - sol.remM);
        long long needL = max(0LL, ia.l - sol.remL);
        if(needM==0 && needL==0){
            // can add directly
            sol.x[a] += 1;
            sol.remM -= ia.m;
            sol.remL -= ia.l;
            sol.value += ia.v;
            return true;
        }
        // try remove one type b
        for(int b=0;b<n;b++){
            if(sol.x[b] <= 0) continue;
            const auto& ib = items[b];
            long long t = max(ceil_div(needM, ib.m), ceil_div(needL, ib.l));
            if(t <= 0) t = 1;
            if(t > sol.x[b]) continue;
            long long deltaV = ia.v - t * ib.v;
            if(deltaV <= 0) continue;
            // apply
            sol.x[a] += 1;
            sol.x[b] -= t;
            sol.remM = sol.remM - ia.m + t * ib.m;
            sol.remL = sol.remL - ia.l + t * ib.l;
            sol.value += deltaV;
            return true;
        }
    }
    return false;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string input, line;
    {
        ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }
    vector<Item> items = parseInput(input);
    int n = items.size();
    if(n==0){
        cout << "{\n}\n";
        return 0;
    }

    // Prepare multiple orderings (strategies)
    vector<vector<int>> strategies;
    // weights alpha from 0..10 on normalized m,l
    for(int a=0;a<=10;a++){
        vector<pair<double,int>> score;
        for(int i=0;i<n;i++){
            double wm = (double)items[i].m / (double)CAP_M;
            double wl = (double)items[i].l / (double)CAP_L;
            double w = a*wm + (10-a)*wl + 1e-12;
            double s = (double)items[i].v / w;
            score.push_back({-s, i});
        }
        sort(score.begin(), score.end());
        vector<int> ord;
        for(auto &p:score) ord.push_back(p.second);
        strategies.push_back(ord);
    }
    // v per mass
    {
        vector<pair<double,int>> score;
        for(int i=0;i<n;i++){
            double s = (double)items[i].v / ((double)items[i].m + 1e-9);
            score.push_back({-s, i});
        }
        sort(score.begin(), score.end());
        vector<int> ord;
        for(auto &p:score) ord.push_back(p.second);
        strategies.push_back(ord);
    }
    // v per volume
    {
        vector<pair<double,int>> score;
        for(int i=0;i<n;i++){
            double s = (double)items[i].v / ((double)items[i].l + 1e-9);
            score.push_back({-s, i});
        }
        sort(score.begin(), score.end());
        vector<int> ord;
        for(auto &p:score) ord.push_back(p.second);
        strategies.push_back(ord);
    }
    // v per max normalized dimension
    {
        vector<pair<double,int>> score;
        for(int i=0;i<n;i++){
            double wm = (double)items[i].m / (double)CAP_M;
            double wl = (double)items[i].l / (double)CAP_L;
            double w = max(wm, wl) + 1e-12;
            double s = (double)items[i].v / w;
            score.push_back({-s, i});
        }
        sort(score.begin(), score.end());
        vector<int> ord;
        for(auto &p:score) ord.push_back(p.second);
        strategies.push_back(ord);
    }

    Solution best;
    best.x.assign(n,0);
    best.value = 0;
    best.remM = CAP_M;
    best.remL = CAP_L;

    for(auto &ord : strategies){
        Solution sol = greedyFill(items, ord);
        // local improvements
        // First try to fill more directly following same order repeatedly
        tryDirectFill(items, ord, sol);
        // hill-climb with single-type removal
        int iter=0;
        const int MAX_ITERS = 2000;
        while(iter < MAX_ITERS){
            bool improved = improveOneSwap(items, sol);
            if(!improved) break;
            // after a successful swap, try direct fill again
            tryDirectFill(items, ord, sol);
            iter++;
        }
        if(sol.value > best.value){
            best = sol;
        }
    }

    // Output JSON with same keys as input order
    cout << "{\n";
    for(int i=0;i<n;i++){
        cout << " \"" << items[i].name << "\": " << best.x[i];
        if(i+1<n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}