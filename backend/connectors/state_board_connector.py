"""
State Medical Board connector for license validation
"""

import logging
from typing import Dict, Any, Optional, List
import asyncio
import random
from datetime import datetime, timedelta

from .base import BaseConnector
from ..config import settings

logger = logging.getLogger(__name__)

class StateBoardConnector(BaseConnector):
    """Connector for State Medical Board validation (Mock implementation)"""
    
    def __init__(self):
        super().__init__(rate_limit=settings.STATE_BOARD_RATE_LIMIT)
        
        # Mock data for different states
        self.mock_licenses = {
            'CA': {
                'valid_licenses': ['A12345', 'B67890', 'C11111', 'D22222', 'E33333'],
                'expired_licenses': ['F44444', 'G55555'],
                'invalid_licenses': ['H66666', 'I77777']
            },
            'NY': {
                'valid_licenses': ['NY123456', 'NY789012', 'NY345678', 'NY901234'],
                'expired_licenses': ['NY567890'],
                'invalid_licenses': ['NY1234567']
            },
            'TX': {
                'valid_licenses': ['TX123456', 'TX789012', 'TX345678'],
                'expired_licenses': ['TX901234'],
                'invalid_licenses': ['TX567890']
            },
            'FL': {
                'valid_licenses': ['ME123456', 'ME789012', 'ME345678'],
                'expired_licenses': ['ME901234'],
                'invalid_licenses': ['ME567890']
            }
        }
    
    async def validate_license(
        self, 
        license_number: str, 
        state: str
    ) -> Dict[str, Any]:
        """Validate medical license against state board"""
        try:
            # Simulate API delay and rate limiting
            await self._rate_limit_check()
            await asyncio.sleep(random.uniform(0.5, 2.0))  # Simulate network delay
            
            if not license_number or not state:
                return {
                    'valid': False,
                    'error': 'License number and state are required',
                    'license_number': license_number,
                    'state': state
                }
            
            # Normalize inputs
            license_clean = license_number.strip().upper()
            state_clean = state.strip().upper()
            
            # Check if state is supported
            if state_clean not in self.mock_licenses:
                return {
                    'valid': False,
                    'error': f'State {state_clean} not supported in mock data',
                    'license_number': license_clean,
                    'state': state_clean,
                    'mock': True
                }
            
            state_data = self.mock_licenses[state_clean]
            
            # Check license validity
            if license_clean in state_data['valid_licenses']:
                # Generate realistic license details
                license_details = await self._generate_valid_license_details(
                    license_clean, state_clean
                )
                
                logger.info(f"License validation successful for {license_clean} in {state_clean}")
                
                return {
                    'valid': True,
                    'license_number': license_clean,
                    'state': state_clean,
                    'status': 'active',
                    'details': license_details,
                    'mock': True
                }
            
            elif license_clean in state_data['expired_licenses']:
                license_details = await self._generate_expired_license_details(
                    license_clean, state_clean
                )
                
                return {
                    'valid': False,
                    'error': 'License is expired',
                    'license_number': license_clean,
                    'state': state_clean,
                    'status': 'expired',
                    'details': license_details,
                    'mock': True
                }
            
            elif license_clean in state_data['invalid_licenses']:
                return {
                    'valid': False,
                    'error': 'License not found in state database',
                    'license_number': license_clean,
                    'state': state_clean,
                    'status': 'not_found',
                    'mock': True
                }
            
            else:
                # License not in mock data - simulate not found
                return {
                    'valid': False,
                    'error': 'License not found in state database',
                    'license_number': license_clean,
                    'state': state_clean,
                    'status': 'not_found',
                    'mock': True
                }
                
        except Exception as e:
            logger.error(f"License validation failed for {license_number} in {state}: {e}")
            return {
                'valid': False,
                'error': f'Validation failed: {str(e)}',
                'license_number': license_number,
                'state': state
            }
    
    async def _generate_valid_license_details(
        self, 
        license_number: str, 
        state: str
    ) -> Dict[str, Any]:
        """Generate realistic valid license details"""
        
        # Generate random but realistic dates
        issue_date = datetime.now() - timedelta(days=random.randint(365, 3650))  # 1-10 years ago
        expiry_date = issue_date + timedelta(days=365 * 3)  # 3-year license
        
        # Add some randomness to expiry (some might be expiring soon)
        if random.random() < 0.1:  # 10% chance of expiring soon
            expiry_date = datetime.now() + timedelta(days=random.randint(1, 90))
        
        return {
            'license_number': license_number,
            'state': state,
            'status': 'active',
            'issue_date': issue_date.isoformat(),
            'expiry_date': expiry_date.isoformat(),
            'license_type': 'Medical Doctor',
            'specialty': random.choice([
                'Internal Medicine', 'Family Medicine', 'Cardiology', 
                'Pediatrics', 'Surgery', 'Radiology', 'Neurology'
            ]),
            'board_certified': random.choice([True, False]),
            'disciplinary_actions': 0,
            'last_updated': datetime.now().isoformat()
        }
    
    async def _generate_expired_license_details(
        self, 
        license_number: str, 
        state: str
    ) -> Dict[str, Any]:
        """Generate realistic expired license details"""
        
        issue_date = datetime.now() - timedelta(days=random.randint(1095, 3650))  # 3-10 years ago
        expiry_date = datetime.now() - timedelta(days=random.randint(1, 365))  # Expired 1-365 days ago
        
        return {
            'license_number': license_number,
            'state': state,
            'status': 'expired',
            'issue_date': issue_date.isoformat(),
            'expiry_date': expiry_date.isoformat(),
            'license_type': 'Medical Doctor',
            'specialty': random.choice([
                'Internal Medicine', 'Family Medicine', 'Cardiology', 
                'Pediatrics', 'Surgery', 'Radiology', 'Neurology'
            ]),
            'board_certified': random.choice([True, False]),
            'disciplinary_actions': random.randint(0, 2),
            'last_updated': datetime.now().isoformat()
        }
    
    async def search_licenses(
        self, 
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        state: Optional[str] = None,
        specialty: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search for licenses by provider information"""
        try:
            await self._rate_limit_check()
            await asyncio.sleep(random.uniform(1.0, 3.0))  # Simulate longer search time
            
            # Mock search results
            mock_results = []
            
            if state and state.upper() in self.mock_licenses:
                state_data = self.mock_licenses[state.upper()]
                
                # Generate mock results
                for license_num in state_data['valid_licenses'][:3]:  # Limit to 3 results
                    result = await self._generate_valid_license_details(license_num, state.upper())
                    result['provider_name'] = f"Dr. {first_name or 'John'} {last_name or 'Doe'}"
                    mock_results.append(result)
            
            return {
                'success': True,
                'result_count': len(mock_results),
                'results': mock_results,
                'search_params': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'state': state,
                    'specialty': specialty
                },
                'mock': True
            }
            
        except Exception as e:
            logger.error(f"License search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'result_count': 0,
                'results': []
            }
    
    async def get_disciplinary_actions(
        self, 
        license_number: str, 
        state: str
    ) -> Dict[str, Any]:
        """Get disciplinary actions for a license"""
        try:
            await self._rate_limit_check()
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Mock disciplinary actions (most licenses have none)
            has_disciplinary = random.random() < 0.15  # 15% chance of disciplinary action
            
            if not has_disciplinary:
                return {
                    'success': True,
                    'license_number': license_number,
                    'state': state,
                    'disciplinary_actions': [],
                    'total_count': 0,
                    'mock': True
                }
            
            # Generate mock disciplinary actions
            actions = []
            action_count = random.randint(1, 3)
            
            for i in range(action_count):
                action_date = datetime.now() - timedelta(days=random.randint(30, 3650))
                
                actions.append({
                    'action_id': f"{state}{license_number}A{i+1}",
                    'action_date': action_date.isoformat(),
                    'action_type': random.choice([
                        'Warning', 'Fine', 'Probation', 'Suspension', 'Reprimand'
                    ]),
                    'description': random.choice([
                        'Failure to maintain continuing education requirements',
                        'Inappropriate prescribing practices',
                        'Failure to maintain adequate medical records',
                        'Professional misconduct',
                        'Violation of state medical practice act'
                    ]),
                    'status': random.choice(['Resolved', 'Active', 'Pending']),
                    'penalty_amount': random.randint(1000, 50000) if random.random() < 0.5 else None
                })
            
            return {
                'success': True,
                'license_number': license_number,
                'state': state,
                'disciplinary_actions': actions,
                'total_count': len(actions),
                'mock': True
            }
            
        except Exception as e:
            logger.error(f"Failed to get disciplinary actions for {license_number}: {e}")
            return {
                'success': False,
                'error': str(e),
                'license_number': license_number,
                'state': state
            }
    
    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Base validation method implementation"""
        return await self.validate_license(
            license_number=data.get('license_number'),
            state=data.get('state')
        )
