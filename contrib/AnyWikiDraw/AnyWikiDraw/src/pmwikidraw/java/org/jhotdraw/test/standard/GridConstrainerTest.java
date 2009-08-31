/*
 * @(#)Test.java
 *
 * Project:		JHotdraw - a GUI framework for technical drawings
 *				http://www.jhotdraw.org
 *				http://jhotdraw.sourceforge.net
 * Copyright:	� by the original author(s) and all contributors
 * License:		Lesser GNU Public License (LGPL)
 *				http://www.opensource.org/licenses/lgpl-license.html
 */
package org.jhotdraw.test.standard;

import org.jhotdraw.standard.GridConstrainer;
import junit.framework.TestCase;
// JUnitDoclet begin import
// JUnitDoclet end import

/*
 * Generated by JUnitDoclet, a tool provided by
 * ObjectFab GmbH under LGPL.
 * Please see www.junitdoclet.org, www.gnu.org
 * and www.objectfab.de for informations about
 * the tool, the licence and the authors.
 */

// JUnitDoclet begin javadoc_class
/**
 * TestCase GridConstrainerTest is generated by
 * JUnitDoclet to hold the tests for GridConstrainer.
 * @see org.jhotdraw.standard.GridConstrainer
 */
// JUnitDoclet end javadoc_class
public class GridConstrainerTest
// JUnitDoclet begin extends_implements
extends TestCase
// JUnitDoclet end extends_implements
{
	// JUnitDoclet begin class
	// instance variables, helper methods, ... put them in this marker
	private GridConstrainer gridconstrainer;
	// JUnitDoclet end class

	/**
	 * Constructor GridConstrainerTest is
	 * basically calling the inherited constructor to
	 * initiate the TestCase for use by the Framework.
	 */
	public GridConstrainerTest(String name) {
		// JUnitDoclet begin method GridConstrainerTest
		super(name);
		// JUnitDoclet end method GridConstrainerTest
	}

	/**
	 * Factory method for instances of the class to be tested.
	 */
	public GridConstrainer createInstance() throws Exception {
		// JUnitDoclet begin method testcase.createInstance
		return new GridConstrainer(5, 5);
		// JUnitDoclet end method testcase.createInstance
	}

	/**
	 * Method setUp is overwriting the framework method to
	 * prepare an instance of this TestCase for a single test.
	 * It's called from the JUnit framework only.
	 */
	protected void setUp() throws Exception {
		// JUnitDoclet begin method testcase.setUp
		super.setUp();
		gridconstrainer = createInstance();
		// JUnitDoclet end method testcase.setUp
	}

	/**
	 * Method tearDown is overwriting the framework method to
	 * clean up after each single test of this TestCase.
	 * It's called from the JUnit framework only.
	 */
	protected void tearDown() throws Exception {
		// JUnitDoclet begin method testcase.tearDown
		gridconstrainer = null;
		super.tearDown();
		// JUnitDoclet end method testcase.tearDown
	}

	// JUnitDoclet begin javadoc_method constrainPoint()
	/**
	 * Method testConstrainPoint is testing constrainPoint
	 * @see org.jhotdraw.standard.GridConstrainer#constrainPoint(java.awt.Point)
	 */
	// JUnitDoclet end javadoc_method constrainPoint()
	public void testConstrainPoint() throws Exception {
		// JUnitDoclet begin method constrainPoint
		// JUnitDoclet end method constrainPoint
	}

	// JUnitDoclet begin javadoc_method getStepX()
	/**
	 * Method testGetStepX is testing getStepX
	 * @see org.jhotdraw.standard.GridConstrainer#getStepX()
	 */
	// JUnitDoclet end javadoc_method getStepX()
	public void testGetStepX() throws Exception {
		// JUnitDoclet begin method getStepX
		// JUnitDoclet end method getStepX
	}

	// JUnitDoclet begin javadoc_method getStepY()
	/**
	 * Method testGetStepY is testing getStepY
	 * @see org.jhotdraw.standard.GridConstrainer#getStepY()
	 */
	// JUnitDoclet end javadoc_method getStepY()
	public void testGetStepY() throws Exception {
		// JUnitDoclet begin method getStepY
		// JUnitDoclet end method getStepY
	}

	// JUnitDoclet begin javadoc_method testVault
	/**
	 * JUnitDoclet moves marker to this method, if there is not match
	 * for them in the regenerated code and if the marker is not empty.
	 * This way, no test gets lost when regenerating after renaming.
	 * <b>Method testVault is supposed to be empty.</b>
	 */
	// JUnitDoclet end javadoc_method testVault
	public void testVault() throws Exception {
		// JUnitDoclet begin method testcase.testVault
		// JUnitDoclet end method testcase.testVault
	}

}
