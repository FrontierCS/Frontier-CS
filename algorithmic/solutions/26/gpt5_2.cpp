#include <bits/stdc++.h>
using namespace std;

struct Node {
    int val;
    int sz;
    uint32_t pri;
    Node *l, *r, *p;
    Node(int v, uint32_t pr): val(v), sz(1), pri(pr), l(nullptr), r(nullptr), p(nullptr) {}
};

inline int getsz(Node* t){ return t ? t->sz : 0; }
inline void upd(Node* t){
    if(!t) return;
    t->sz = 1 + getsz(t->l) + getsz(t->r);
    if(t->l) t->l->p = t;
    if(t->r) t->r->p = t;
}

Node* merge(Node* a, Node* b){
    if(!a){ if(b) b->p = nullptr; return b; }
    if(!b){ if(a) a->p = nullptr; return a; }
    if(a->pri < b->pri){
        a->r = merge(a->r, b);
        if(a->r) a->r->p = a;
        upd(a);
        a->p = nullptr;
        return a;
    }else{
        b->l = merge(a, b->l);
        if(b->l) b->l->p = b;
        upd(b);
        b->p = nullptr;
        return b;
    }
}

void split(Node* t, int k, Node* &a, Node* &b){ // first k nodes to a, rest to b
    if(!t){ a = b = nullptr; return; }
    int lsz = getsz(t->l);
    if(k <= lsz){
        split(t->l, k, a, t->l);
        if(t->l) t->l->p = t;
        b = t;
        b->p = nullptr;
        upd(b);
    }else{
        split(t->r, k - lsz - 1, t->r, b);
        if(t->r) t->r->p = t;
        a = t;
        a->p = nullptr;
        upd(a);
    }
}

int getIndex(Node* x){
    int idx = getsz(x->l) + 1;
    while(x->p){
        if(x == x->p->r){
            idx += getsz(x->p->l) + 1;
        }
        x = x->p;
    }
    return idx;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> v(n+1), pos(n+1);
    for(int i=1;i<=n;i++){
        cin >> v[i];
        pos[v[i]] = i;
    }

    // Compute LIS on positions sequence pos[1..n]
    vector<int> tailPos;
    vector<int> tailId;
    vector<int> parent(n+1, 0);
    vector<int> dpLenVal(n+1, 0);
    for(int val=1; val<=n; ++val){
        int p = pos[val];
        int idx = lower_bound(tailPos.begin(), tailPos.end(), p) - tailPos.begin();
        if(idx == (int)tailPos.size()){
            tailPos.push_back(p);
            tailId.push_back(val);
        }else{
            tailPos[idx] = p;
            tailId[idx] = val;
        }
        parent[val] = (idx > 0 ? tailId[idx-1] : 0);
        dpLenVal[val] = idx + 1;
    }
    int LIS_len = (int)tailPos.size();
    int lastVal = tailId[LIS_len-1];
    vector<int> lisVals;
    while(lastVal){
        lisVals.push_back(lastVal);
        lastVal = parent[lastVal];
    }
    reverse(lisVals.begin(), lisVals.end());
    vector<char> inLIS(n+1, false);
    for(int x: lisVals) inLIS[x] = true;

    // Build treap from initial permutation order
    std::mt19937 rng(712367);
    vector<Node*> nodesByVal(n+1, nullptr);
    Node* root = nullptr;
    for(int i=1;i<=n;i++){
        Node* nd = new Node(v[i], rng());
        nodesByVal[v[i]] = nd;
        root = merge(root, nd);
    }

    vector<pair<int,int>> moves;
    long long sumY = 0;
    int moveCount = 0;

    auto moveTo = [&](int value, int yFinal){
        Node* t = nodesByVal[value];
        int x = getIndex(t);
        if(x == yFinal){
            moves.emplace_back(x, yFinal);
            sumY += yFinal;
            moveCount++;
            return;
        }
        Node *A, *B, *C, *D;
        split(root, x-1, A, B);
        split(B, 1, C, D);
        // C should be t
        root = merge(A, D);
        int insertPos = yFinal;
        if(x < yFinal) insertPos--;
        Node *L, *R;
        split(root, insertPos-1, L, R);
        root = merge(merge(L, C), R);
        moves.emplace_back(x, yFinal);
        sumY += yFinal;
        moveCount++;
    };

    if(LIS_len > 0){
        int lm = lisVals.back();
        // Rightmost segment: values > lm not in LIS, process in descending order, insert after lm at y = pos(lm)+1 (adjust if x < pos(lm))
        for(int val = n; val > lm; --val){
            if(inLIS[val]) continue;
            int posLM = getIndex(nodesByVal[lm]);
            int x = getIndex(nodesByVal[val]);
            int y = (posLM == n ? n : posLM + 1);
            if(x < posLM) y = y - 1; // after removal, lm shifts left by one
            moveTo(val, y);
        }
        // Middle segments: for i from m-1 down to 1, process values between lisVals[i-1] and lisVals[i] in ascending order, insert before lisVals[i]
        for(int i = (int)lisVals.size()-1; i >= 1; --i){
            int L = lisVals[i-1], R = lisVals[i];
            for(int val = L+1; val < R; ++val){
                if(inLIS[val]) continue;
                int posR = getIndex(nodesByVal[R]);
                int x = getIndex(nodesByVal[val]);
                int y = posR;
                if(x < posR) y = y - 1; // after removal, R shifts left
                moveTo(val, y);
            }
        }
        // Leftmost segment: values < lisVals[0] not in LIS, process in descending order, insert at y=1
        int first = lisVals[0];
        for(int val = first - 1; val >= 1; --val){
            if(inLIS[val]) continue;
            moveTo(val, 1);
        }
    }else{
        // No LIS? (n==0) but for safety; otherwise move everything to sort: insert in increasing at end
        for(int val = 1; val <= n; ++val){
            int x = getIndex(nodesByVal[val]);
            moveTo(val, n);
        }
    }

    long long finalCost = (sumY + 1LL) * (moveCount + 1LL);
    cout << finalCost << " " << moveCount << "\n";
    for(auto &pr: moves){
        cout << pr.first << " " << pr.second << "\n";
    }
    return 0;
}