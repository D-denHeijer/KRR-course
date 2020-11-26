from planning import PlanningProblem, Action, Expr, expr
import planning
import clingo
import re

#initialize the planning to None and change if optimal planning is found
planning = None

def solve_planning_problem_using_ASP(planning_problem,t_max):
    """
    Parameters:
        planning_problem (PlanningProblem): Planning problem for which a shortest plan is to be found.
        t_max (int): The upper bound on the length of plans to consider.

    Returns:
        (list(Expr)): A list of expressions (each of which specifies a ground action) that composes
        a shortest plan for planning_problem (if some plan of length at most t_max exists),
        and None otherwise.
    """

    def encode_init_ASP(planning_problem, t_max):
        """
        Method for encoding the initial statements into ASP
        input: planning problem in PDDL
        returns: planning problem in ASP encoding
        """
        #encode t_max time steps
        asp_code = ""
        asp_code += "#const tMax={}.\n".format(t_max-1)
        asp_code += "time(0..tMax).\n"

        #encode initial statements as state(T, init(x,y)) for T=0
        #swapcase used to switch caps and lowercase for different representation
        #of variables and constants in DPPL vs ASP
        for init in planning_problem.initial:
            asp_code += "state(0, {}).\n".format(init.__repr__().swapcase())

        return asp_code

    def encode_actions_ASP(planning_problem):
        """
        Method for encoding the actions into ASP
        input: planning problem in PDDL
        returns: planning problem in ASP encoding
        """
        asp_code = ""
        for action in planning_problem.actions:
            available_action = "available(Time, {}) :- not goal_saved(Time), time(Time)".format(action.__repr__().swapcase())
            if not action.precond:
                available_action = available_action
            else:
                for prec in action.precond:
                        if str(prec)[0] == '~': #check if a negation is present to alter rule to not state
                            prec = expr(str(prec)[1:])
                            available_action += ", not state(Time, {})".format(prec.__repr__().swapcase())
                        else:
                            available_action += ", state(Time, {})".format(prec.__repr__().swapcase())

            fluent = "state(Time, S) :- time(Time), state(Time-1, S), chosen(Time-1, {})".format(action.__repr__().swapcase())
            effect = ""
            for effects in action.effect:
                if str(effects)[0] == '~': #check if a negation is present to alter rule to not same
                    fluent += ", S!={}".format(str(effects)[1:].swapcase())
                else:
                    effect += "state(Time, {}) :- time(Time), chosen(Time-1, {}). \n".format(effects.__repr__().swapcase(), action.__repr__().swapcase())

            available_rule = "1{chosen(Time, A) : available(Time, A)}1 :- time(Time), available(Time, _). \n"
            asp_code += effect + fluent + ". \n" + available_action + ". \n" + available_rule

        return asp_code

    def encode_goals_ASP(planning_problem):
        """
        Method for encoding the goals into ASP
        input: planning problem in PDDL
        returns: planning problem in ASP encoding
        """
        asp_code = ""
        goallist = []
        for goal in planning_problem.goals:
            if str(goal)[0] == '~': #check if a negation is present to alter rule to not state
                goal = expr(str(goal)[1:])
                goallist += ["not state(Time, {})".format(goal.__repr__().swapcase())]
            else:
                goallist += ["state(Time, {})".format(goal.__repr__().swapcase())]

        #add all goal rules, constraints and optimizations
        asp_code += "goal(Time) :- " + "{}. \n".format(', '.join(goallist))
        asp_code += "goal_saved(Time) :- goal(Time). \n"
        asp_code += "goal_saved(Time) :- time(Time), goal_saved(Time-1). \n"
        #constraint
        asp_code += ":- time(Time), not goal(_). \n"
        #optimization statement
        asp_code += "#minimize{Time : goal(Time)}. \n"
        #show the chosen in answer set
        asp_code += '#show chosen/2. \n'

        return asp_code

    def return_plan(sorted_model):
        """
        Method to extract the planning from the model
        Probably not the best way to do it but could not fix it otherwise
        """
        plan_length = len(sorted_model)
        #used to order list according to T in chose(T, A)
        plan = [None]*plan_length
        for plans in sorted_model:
            #find all words in the plan
            words = re.findall(r'\w+', plans)
            #extract action
            action = words[2].swapcase()
            #extract arguments
            arguments = [word.swapcase() for word in words[3:]]
            plan[int(words[1])] = action + "({})".format(', '.join(arguments))

        return plan

    def on_model(model):
        """
        check if optimal model, if optimal model,
        sort results and return planning
        """
        if model.optimality_proven == True:
            model = [str(atom) for atom in model.symbols(shown=True)]
            model.sort()
            global planning
            planning = return_plan(model)

    #create the ASP encoding
    asp_code = ""
    asp_code += encode_init_ASP(planning_problem, t_max)
    asp_code += encode_actions_ASP(planning_problem)
    asp_code += encode_goals_ASP(planning_problem)

    #solve the ASP encoding
    control = clingo.Control()
    control.add("base", [], asp_code)
    control.ground([("base", [])])

    #optimization statements, show 1 model
    control.configuration.solve.opt_mode = "optN"
    control.configuration.solve.models = 1

    #need this to get planning back, must be another way to extract from clingo.model
    answer = control.solve(on_model=on_model)
    #return None if no plan else return planning
    return planning
